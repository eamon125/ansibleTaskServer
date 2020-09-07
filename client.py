import json
import requests

data = {
	'job_id': 1,
    'module': 'rabbitmq',
    'type': 'playbook',
    'tags': ['install'],
	'inventory_data':{
		'all': {
			'hosts': [{
				'hostname': '192.168.6.119',
				'ansible_ssh_user': 'root',
				'ansible_ssh_pass': 'redhat',
				"pkg_version": 'rabbitmq_server-3.8.0',  #包名，自动补全.tar.gz
				"pkg_erlang": 'erlang',
				"rabbitmq_base": '/home/redis',
				"rabbitmq_user": 'redis',
				"rabbitmq_group": 'redis',
				"rabbitmq_username": 'admin',
				"rabbitmq_password": '123456'
			}],
			'vars': {}
		},
		'telegraf': {
			'hosts': [{
				'hostname': '192.168.6.119',
				'ansible_ssh_user': 'root',
				'ansible_ssh_pass': 'redhat',
			}],
			'vars': {
				"pkg_version": 'rabbitmq_server-3.8.0',  #包名，自动补全.tar.gz
				"pkg_erlang": 'erlang',
				"rabbitmq_base": '/home/redis',
				"rabbitmq_user": 'redis',
				"rabbitmq_group": 'redis',
				"rabbitmq_username": 'admin',
				"rabbitmq_password": '123456'
			}
		}
	}
}


data = {
	'file': '/opt/test_file',
	'info': [{'hostname': '10.1.248.125',
			'ansible_ssh_user': 'weblogic',
			'ansible_ssh_pass': 'WEj2&125'}]
}



data = json.dumps(data)
res = requests.post(url='http://127.0.0.1:8080/adhoc/file/delete', data=data)


# data = {'job_id': 1}
# data = json.dumps(data)
# res = requests.post(url='http://127.0.0.1:8080/play/task/stop', data=data)



print('response is ----> ', res)