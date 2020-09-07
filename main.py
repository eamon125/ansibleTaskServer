# -*- coding:utf-8 -*-
from japronto import Application
import concurrent
import multiprocessing
import time
import sys
import os
import json
import configs
import configparser
import pickle
import yaml
import datetime
from db.db import initDB, ExecuteSql
from internal.ansible_api.api import PlayAPI, AdHocAPI
from internal.ansible_api.callback import CallbackDefault
from json import JSONDecodeError
from configs import play_config, settings
from utils.utils import queryPgSql

TASK_PROCESS = {}


def playConfigs(request):
    play_fields = play_config._fields
    play_configs = {k:{} for k in play_config._fields}
    for play_name in play_fields:
        play_conf = os.path.join(os.path.dirname(sys.argv[0]), "configs/plays/"+play_name+".ini")
        config = configparser.ConfigParser()
        config.read(play_conf)
        sections = config.sections()
        setting_map = {s: {} for s in sections if len(s.split(":")) == 1}
        for section in sections:
            s_list = section.split(":")
            if len(s_list) == 1:
                if section == "all":
                    ops = config.options(section)
                    for op in ops:
                        setting_map[section][op] = eval(config.get(section, op))
                else:
                    ops = config.options(section)
                    for op in ops:
                        if "host_vars" not in list(setting_map[section].keys()):
                            setting_map[section].update({"host_vars":{}})
                        setting_map[section]["host_vars"][op] = eval(config.get(section, op))
            elif len(s_list) == 2:
                ops = config.options(section)
                for op in ops:
                    if "group_vars" not in list(setting_map[s_list[0]].keys()):
                        setting_map[s_list[0]].update({"group_vars":{}})
                    setting_map[s_list[0]]["group_vars"][op] = eval(config.get(section, op))
        section_dict = eval("play_config.%s._asdict()" % play_name)
        for k, v in section_dict.items():
            if k == "alias":
                play_configs[play_name]["des"] = v
            if k not in ["alias", "checkup", "checkname"]:
                if "tags" not in list(play_configs[play_name].keys()):
                    play_configs[play_name]["tags"] = {}
                play_configs[play_name]["tags"][k] = v
        play_configs[play_name]["inventory_vars"] = setting_map

    return request.Response(code=200, text=json.dumps(play_configs))


# Views handle logic, take request as a parameter and
# returns Response object back to the client
def tasks(request):
    try:
        data = request.json
    except JSONDecodeError:
        pass
    else:
        configs.TASK_QUEUE.put(data)
    return request.Response(code=200, text="success")


# get file dirs
def fileDirs(request):
    dir_data = {'type': '',
                'file': '',
                'inventory_data': {'all': {}}}
    try:
        data = request.text
        data = eval(data)
    except JSONDecodeError:
        pass
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        if "module" in list(dir_data.keys()):
            return request.Response(code=200, text="success")
        else:
            dir_data['module'] = 'getfile'
            dir_data['type'] = 'adhoc'
            dir_data['file'] = data['file']
            dir_data['inventory_data']['all']['hosts'] = data['info']
            dir_data['inventory_data']['all']['vars'] = {}
            configs.TASK_QUEUE.put(dir_data)
    return request.Response(code=200, text="success")


# delete log files
def delFile(request):
    file_data = {'type': '',
                'file': '',
                'inventory_data': {'all': {}}}
    try:
        data = request.json
    except JSONDecodeError:
        pass
    else:
        file_data['module'] = 'delete'
        file_data['type'] = 'adhoc'
        file_data['file'] = data['file']
        file_data['inventory_data']['all']['hosts'] = data['info']
        file_data['inventory_data']['all']['vars'] = {}
        configs.TASK_QUEUE.put(file_data)
    return request.Response(code=200, text="success")


# Stop task process.
def stop_task(request):
    try:
        res = request.json
    except Exception as e:
        return request.Response(code=400, text="jobId error")
    
    job_id = res['job_id']

    if dict(var_dict).get(job_id):
        pid = var_dict[job_id]
        try:
            os.kill(int(pid), 0)
        except OSError:
            return request.Response(code=200, json={'msg': "process killed"})
        else:
            return request.Response(code=201, json={'msg': "process killed successly"})
    else:
        return request.Response(code=202, json={'msg': "process not exist"})


# 查询某一个job_jid的执行过程
def job_log(request):
    job_info = eval("""{0.query}
    """.strip().format(request))
    if not job_info:
        return request.Response(code=200, json={'msg': "query string [jid] not found"})

    jid = job_info["jid"]
    sql = """SELECT * FROM tk_jobs WHERE jid = '%s' ORDER BY id;""" % jid
    rs =  queryPgSql(sql)
    data = []
    for r in rs:
        data.append({"id": r[0], "jid": r[1], "host": r[2], "status": r[3], "msg": r[4], "task": r[5], "service_name": r[6], "time": r[7].strftime("%Y-%m-%d %H:%M:%S")})

    return request.Response(code=200, json=data)


# 查询某一个job_id的执行结果
def job_result(request):
    job_info = eval("""{0.query}
    """.strip().format(request))
    if not job_info:
        return request.Response(code=200, json={'msg': "query string [jid] not found"})

    jid = job_info["jid"]
    sql = """SELECT * FROM tk_results WHERE jid = '%s' ORDER BY id;""" % jid
    rs =  queryPgSql(sql)
    data = []
    for r in rs:
        data.append({"id": r[0], "jid": r[1], "host": r[2], "status": r[3], "msg": r[4], "service_name": r[5], "time": r[6].strftime("%Y-%m-%d %H:%M:%S")})

    return request.Response(code=200, json=data)

# 存储playbook主机清单
def SavePlayInventory(request):
    try:
        data = request.text
        data = eval(data)
    except JSONDecodeError:
        return
    except Exception as e:
        import traceback
        traceback.print_exc()
        return

    module = data['module']
    type = data['type']
    tags = data['tags']
    inventoryData = data['inventory_data']
    createTime = datetime.datetime()
    sqlStr = """
        insert into public.tk_inventory(module, type, tags, inventoryData, create_time) 
        values(%s, %s, %s, %s, %s);
    """ % (module, type, tags, inventoryData, createTime)
    result = ExecuteSql(sqlStr)
    return request.Response(code=result[0], text=result[1])

# 展示playbook可用模板
def showPlays(request):
    plays = []
    play_dir = os.path.join(configs.base_dir, configs.settings.play.play_template_path)
    files = os.listdir(play_dir)
    for file in files:
        with open(os.path.join(play_dir, file), "r") as f:
            content = yaml.safe_load(f.read().strip())
            if content is None:
                continue
            plays += content

    return request.Response(code=200, text=json.dumps(plays))

# 存储playbook组合数据并生成playbook 文件
def SavePlays(request):
    try:
        data = request.text
        data = eval(data)
    except JSONDecodeError:
        return
    except Exception as e:
        import traceback
        traceback.print_exc()
        return

    inventoryId = data['inventory_id']
    playName = data['play_name']
    taskName = data['task_name']
    jsonData = data['data']
    createTime = datetime.datetime()
    sqlStr = """
        insert into public.tk_play_task(inventory_id, play_name, task_name, json_data, create_time) 
        values(%s, %s, %s, %s, %s);
    """ % (inventoryId, playName, taskName, jsonData, createTime)
    result = ExecuteSql(sqlStr)
    return request.Response(code=result[0], text=result[1])

## api服务
def api_server(common_var):
    global var_dict
    var_dict = common_var
    app = Application()
    app.router.add_route('/play/task', tasks, 'POST')
    app.router.add_route('/play/configs', playConfigs, 'GET')
    app.router.add_route('/play/task/stop', stop_task, 'POST')
    app.router.add_route('/adhoc/file/delete', delFile, 'POST')
    app.router.add_route('/adhoc/files/list', fileDirs, 'POST')
    app.router.add_route('/play/template/list', showPlays, 'GET')
    app.router.add_route('/play/template/save', SavePlays, 'POST')
    app.router.add_route('/play/inventory/save', SavePlayInventory, 'POST')
    app.router.add_route('/job/log', job_log, 'GET')
    app.router.add_route('/job/result', job_result, 'GET')
    app.run(host=settings.server.host, port=int(settings.server.port), worker_num=None, reload=False, debug=True)


## 执行playbook任务
def execute_task(data):
    api = PlayAPI(service=data['module'], inventory_json=json.dumps(data['inventory_data']),  job_id = data['job_id'],  host='all')
    # print("++++++++", api.job_id,api.service_name)
    api.execute(tag=data['tags'], callback_default=False)

## 执行adhoc任务
def execute_adhoc(file_data):
    data = file_data
    DELETE_FILE = dict(action=dict(module='file', args="dest=%s state=absent"%data['file']))
    adhoc_api = AdHocAPI(module='file', host='all', inventory_json=data['inventory_data'])
    adhoc_api.execute(DELETE_FILE, callback_default=False)


## 获取文件目录结构
def execute_adhoc_files(data):
    FILE_SHELL = dict(action=dict(module='script', args="get_file.py %s executable=python"%data['file']))
    adhoc_api = AdHocAPI(module='script', host='all', inventory_json=data['inventory_data'])
    adhoc_api.execute(FILE_SHELL, callback_default=True)


## 处理ansible任务队列
def task_producer(common_var):
    while True:
        if not configs.TASK_QUEUE.empty():
            data = configs.TASK_QUEUE.get()
            if data['type'] == 'playbook':
                ## 执行任务进程
                tasks_execute = multiprocessing.Process(
                    name='execute_task',
                    target=execute_task,
                    args=(data,)
                )
        
                tasks_execute.daemon = False
                tasks_execute.start()
                common_var[data['job_id']] = tasks_execute.pid
            else:
                if data['module'] == 'delete':
                    adhoc_task = multiprocessing.Process(
                        name='delete_task',
                        target=execute_adhoc,
                        args=(data,)
                    )
                else:
                    adhoc_task = multiprocessing.Process(
                        name='get_file_list',
                        target=execute_adhoc_files,
                        args=(data,)
                    )
                adhoc_task.daemon = False
                adhoc_task.start()


def main():
    # 启动程序时初始化数据库
    initDB()

    manager = multiprocessing.Manager()
    common_var = manager.dict()

    ## api服务的进程
    api_proc = multiprocessing.Process(
        name='api_server',
        target=api_server,
        args=(common_var,)
    )
    api_proc.daemon = False
    api_proc.start()

    ## task任务消费进程
    tasks_proc = multiprocessing.Process(
        name='tasks',
        target=task_producer,
        args=(common_var,)
    )
    tasks_proc.daemon = False
    tasks_proc.start()

    while True:
        pass

if __name__ == "__main__":
    main()
