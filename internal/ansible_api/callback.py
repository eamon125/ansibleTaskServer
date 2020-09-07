# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2017 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    callback: default
    type: stdout
    short_description: default Ansible screen output
    version_added: historical
    description:
        - This is the default output callback for ansible-playbook.
    extends_documentation_fragment:
      - default_callback
    requirements:
      - set as stdout in configuration
'''

from ansible import constants as C
from ansible import context
from ansible.playbook.task_include import TaskInclude
from ansible.plugins.callback import CallbackBase
from ansible.utils.color import colorize, hostcolor

from utils.utils import excPgSql
from datetime import datetime


# These values use ansible.constants for historical reasons, mostly to allow
# unmodified derivative plugins to work. However, newer options added to the
# plugin are not also added to ansible.constants, so authors of derivative
# callback plugins will eventually need to add a reference to the common docs
# fragment for the 'default' callback plugin

# these are used to provide backwards compat with old plugins that subclass from default
# but still don't use the new config system and/or fail to document the options
COMPAT_OPTIONS = (('display_skipped_hosts', C.DISPLAY_SKIPPED_HOSTS),
                  ('display_ok_hosts', True),
                  ('show_custom_stats', C.SHOW_CUSTOM_STATS),
                  ('display_failed_stderr', False),)


class CallbackDefault(CallbackBase):

    '''
    This is the default callback interface, which simply prints messages
    to stdout when new callback events are received.
    '''

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'stdout'
    CALLBACK_NAME = 'default'

    def __init__(self, job_id, service_name):
        super(CallbackDefault, self).__init__()
        self.job_id = job_id
        self.service_name = service_name

        self._play = None
        self._last_task_banner = None
        self._last_task_name = None
        self._task_type_cache = {}

    def set_options(self, task_keys=None, var_options=None, direct=None):

        super(CallbackDefault, self).set_options(task_keys=task_keys, var_options=var_options, direct=direct)

        # for backwards compat with plugins subclassing default, fallback to constants
        for option, constant in COMPAT_OPTIONS:
            try:
                value = self.get_option(option)
            except (AttributeError, KeyError):
                value = constant
            setattr(self, option, value)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        r = result.__dict__
        host = r["_host"]
        task = r["_task"]
        stderr = r["_result"]["msg"]
        t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sql = """INSERT INTO tk_jobs (jid, host, status, msg, task, service_name, create_time, update_time) VALUES
                    ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');""" % (self.job_id,host, "Failed", stderr.replace("'", '"'), task, self.service_name, t, t)
        excPgSql(sql)

    def v2_runner_on_ok(self, result):
        r = result.__dict__
        host = r["_host"]
        task = r["_task"]
        
        t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        excPgSql("""INSERT INTO tk_jobs (jid, host, status, msg, task, service_name, create_time, update_time) VALUES
                    ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');""" % (self.job_id,host, "OK", "Running success!", task, self.service_name, t, t))

    def v2_runner_on_skipped(self, result):
        pass

    def v2_runner_on_unreachable(self, result):
        r = result.__dict__
        host = r["_host"]
        task = r["_task"]
        t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        excPgSql("""INSERT INTO tk_jobs (jid, host, status, msg, task, service_name, create_time, update_time) VALUES
                    ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');""" % (self.job_id,host, "Unreachable", "Host unreachable!", task, self.service_name, t, t))


    def v2_playbook_on_no_hosts_matched(self):
        self._display.display("skipping: no hosts matched", color=C.COLOR_SKIP)

    def v2_playbook_on_no_hosts_remaining(self):
        self._display.banner("NO MORE HOSTS LEFT")

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_start(task, prefix='TASK')

    def _task_start(self, task, prefix=None):
        # Cache output prefix for task if provided
        # This is needed to properly display 'RUNNING HANDLER' and similar
        # when hiding skipped/ok task results
        if prefix is not None:
            self._task_type_cache[task._uuid] = prefix

        # Preserve task name, as all vars may not be available for templating
        # when we need it later
        if self._play.strategy == 'free':
            # Explicitly set to None for strategy 'free' to account for any cached
            # task title from a previous non-free play
            self._last_task_name = None
        else:
            self._last_task_name = task.get_name().strip()


    def _print_task_banner(self, task):
        # args can be specified as no_log in several places: in the task or in
        # the argument spec.  We can check whether the task is no_log but the
        # argument spec can't be because that is only run on the target
        # machine and we haven't run it thereyet at this time.
        #
        # So we give people a config option to affect display of the args so
        # that they can secure this if they feel that their stdout is insecure
        # (shoulder surfing, logging stdout straight to a file, etc).
        args = ''
        if not task.no_log and C.DISPLAY_ARGS_TO_STDOUT:
            args = u', '.join(u'%s=%s' % a for a in task.args.items())
            args = u' %s' % args

        prefix = self._task_type_cache.get(task._uuid, 'TASK')

        # Use cached task name
        task_name = self._last_task_name
        if task_name is None:
            task_name = task.get_name().strip()

        self._display.banner(u"%s [%s%s]" % (prefix, task_name, args))
        if self._display.verbosity >= 2:
            path = task.get_path()
            if path:
                self._display.display(u"task path: %s" % path, color=C.COLOR_DEBUG)

        self._last_task_banner = task._uuid

    def v2_playbook_on_cleanup_task_start(self, task):
        self._task_start(task, prefix='CLEANUP TASK')

    def v2_playbook_on_handler_task_start(self, task):
        self._task_start(task, prefix='RUNNING HANDLER')

    def v2_playbook_on_play_start(self, play):
        name = play.get_name().strip()
        if not name:
            msg = u"PLAY"
        else:
            msg = u"PLAY [%s]" % name

        self._play = play

        self._display.banner(msg)

    def v2_on_file_diff(self, result):
        if result._task.loop and 'results' in result._result:
            for res in result._result['results']:
                if 'diff' in res and res['diff'] and res.get('changed', False):
                    diff = self._get_diff(res['diff'])
                    if diff:
                        if self._last_task_banner != result._task._uuid:
                            self._print_task_banner(result._task)
                        self._display.display(diff)
        elif 'diff' in result._result and result._result['diff'] and result._result.get('changed', False):
            diff = self._get_diff(result._result['diff'])
            if diff:
                if self._last_task_banner != result._task._uuid:
                    self._print_task_banner(result._task)
                self._display.display(diff)

    def v2_runner_item_on_ok(self, result):
        pass

    def v2_runner_item_on_failed(self, result):
        pass

    def v2_runner_item_on_skipped(self, result):
        pass

    def v2_playbook_on_include(self, included_file):
        msg = 'included: %s for %s' % (included_file._filename, ", ".join([h.name for h in included_file._hosts]))
        if 'item' in included_file._args:
            msg += " => (item=%s)" % (self._get_item_label(included_file._args),)
        self._display.display(msg, color=C.COLOR_SKIP)

    def v2_playbook_on_stats(self, stats):
        self._display.banner("PLAY RECAP")

        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)

            tm = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            excPgSql("""INSERT INTO tk_results (jid, host, status, msg, service_name, create_time, update_time) VALUES
                    ('%s', '%s', '%s', '%s', '%s', '%s', '%s');""" % (self.job_id,h , "Finished", str(t).replace("'", '"'), self.service_name, tm, tm))
  
            self._display.display(
                u"%s : %s %s %s %s %s %s %s" % (
                    hostcolor(h, t),
                    colorize(u'ok', t['ok'], C.COLOR_OK),
                    colorize(u'changed', t['changed'], C.COLOR_CHANGED),
                    colorize(u'unreachable', t['unreachable'], C.COLOR_UNREACHABLE),
                    colorize(u'failed', t['failures'], C.COLOR_ERROR),
                    colorize(u'skipped', t['skipped'], C.COLOR_SKIP),
                    colorize(u'rescued', t['rescued'], C.COLOR_OK),
                    colorize(u'ignored', t['ignored'], C.COLOR_WARN),
                ),
                screen_only=True
            )

            self._display.display(
                u"%s : %s %s %s %s %s %s %s" % (
                    hostcolor(h, t, False),
                    colorize(u'ok', t['ok'], None),
                    colorize(u'changed', t['changed'], None),
                    colorize(u'unreachable', t['unreachable'], None),
                    colorize(u'failed', t['failures'], None),
                    colorize(u'skipped', t['skipped'], None),
                    colorize(u'rescued', t['rescued'], None),
                    colorize(u'ignored', t['ignored'], None),
                ),
                log_only=True
            )

        self._display.display("", screen_only=True)

        # print custom stats if required
        if stats.custom and self.show_custom_stats:
            self._display.banner("CUSTOM STATS: ")
            # per host
            # TODO: come up with 'pretty format'
            for k in sorted(stats.custom.keys()):
                if k == '_run':
                    continue
                self._display.display('\t%s: %s' % (k, self._dump_results(stats.custom[k], indent=1).replace('\n', '')))

            # print per run custom stats
            if '_run' in stats.custom:
                self._display.display("", screen_only=True)
                self._display.display('\tRUN: %s' % self._dump_results(stats.custom['_run'], indent=1).replace('\n', ''))
            self._display.display("", screen_only=True)
    
    def v2_runner_retry(self, result):
        task_name = result.task_name or result._task
        msg = "FAILED - RETRYING: %s (%d retries left)." % (task_name, result._result['retries'] - result._result['attempts'])
        if (self._display.verbosity > 2 or '_ansible_verbose_always' in result._result) and '_ansible_verbose_override' not in result._result:
            msg += "Result was: %s" % self._dump_results(result._result)
        self._display.display(msg, color=C.COLOR_DEBUG)

    def v2_playbook_on_notify(self, handler, host):
        if self._display.verbosity > 1:
            self._display.display("NOTIFIED HANDLER %s for %s" % (handler.get_name(), host), color=C.COLOR_VERBOSE, screen_only=True)
