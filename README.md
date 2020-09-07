# TaskServer程序操作手册
#Python #Ansible #自动化部署
## 一、简介
`TaskServer`用于自动化执行playbook任务。

## 二、项目结构
> 以下列举项目中常用（及核心）结构。
```
TaskServer                 -- 项目目录
├── configs                -- 项目配置文件存放地址
    ├── __init__.py
    ├── adhoc              -- adhoc的模板
    ├── playbook           -- playbook 模板
    ├── adhoc.ini          -- adhoc 的配置文件
    ├── configs.go         -- go文件 初始化配置
    ├── parser.go          -- go文件 配置文件解析
    ├── play.ini           -- playbook的配置文件
    ├── playbook.ini       -- playbook模板的配置文件
    └── settings.ini       -- 配置文件
├── db                     -- 数据库操作
    ├── __init__.py         
    ├── db.py              -- 数据库操作方法实现
    ├── sql.py             -- 数据库操作的SQL语句
├── internal               -- 公共Python库
│   └── ansible_api        -- 二次开发后的ansible接口
├── logs                   -- 日志存放处
│   ├── api.log            -- restful 接口的日志
│   └── task.log           -- 远程任务执行器的日志
├── packages               -- 第三方依赖存放库
│   ├── glibc-2.14         -- Glibc（主要用于rhel7以下系统）
│   ├── miniconda3         -- conda提供的python环境（包含python程序的所有依赖）
│   ├── sshpass-rh6        -- ssh远程连接依赖（rhel6适用）
│   └── sshpass-rh7        -- ssh远程连接依赖（rhel7适用）
├── scripts                -- 自动化程序脚本存放处
│   ├── playbooks          -- playbook入口文件，及分组变量配置文件存放
│   └── roles              -- ansible role存放处
├── tmp                    -- 存放Py远程执行器的group pid
│   └── task.gpid
├── utils                  -- 公共方法
    ├── utils.go           -- 公共方法go文件
│   └── utils.py           -- 公共方法python文件
├── __init__.py
├── main.py                -- python远程任务执行器的入口文件
├── README.md              -- TaskServer 程序使用文档
├── requirements.txt       -- python依赖库
├── taskCtl                -- TaskServer 程序启动入口
└── taskCtl.go             -- TaskServer 程序启动go文件
```

## 三、程序配置
> 整个项目的配置文件位于`configs/settings.ini`
```vim
[listner]
# 远程任务的进程池大小
pool_max_size = 100

[play]
# 默认ansible playbook入口文件存放位置
playbook_path = scripts/playbooks
# 默认ansible role文件存放位置
roles_path = scripts/roles
# ansible远程连接方式，paramiko为python的ssh库，建议使用smart，smart为sshpass。
# ssh_connection = paramiko
ssh_connection = smart
# ansible子进程的fork数量
fork = 50
# playbook模板文件存放位置
play_template_path = configs/playbook

[adhoc] # 功能尚未开放，暂时可忽略
module_path = scripts/modules
# ssh_connection = paramiko
ssh_connection = smart
fork = 50

[server]  # 服务器配置
# 自动化执行器服务地址
host = 0.0.0.0
# 自动化执行器服务端口
port = 8989
# rhel7时请填写7；rhel6时请填写6
os = 7  
# 日志存放地址
log_file = logs/task.log

[db]
# 数据库类型
dbtype = postgres
# 数据库名称
dbname = taskserver
# 数据库用户
dbuser = postgres
# 数据库密码
dbpass = postgres
# 数据库ip地址
dbhost = 127.0.0.1
# 数据库端口号
dbport = 5435

# log配置项
[logging]
```
## 四、远程执行任务流程
### 4.1 远程执行器任务流程
> 远程执行任务流程如下：
> 1. inventory主机清单
> 2. ansible playbook模板组合
> 3. 执行组合后的playbook模板任务
#### 4.1.1 inventory主机清单
> 以下列举一个执行安装rabbitmq的inventory的结构：`rabbitmq `。
```
{
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
```
### 4.2 playbook模板组合

（1）前端需要传入的变量结构
```
[
    {
        "name": "拷贝模板到目标主机",
        "template": {
            "src": "模板文件名称 || {}",
            "dest": "目标主机路径 || {}"
        },
        "tags": [
            "tcpy",
            "config"
        ]
    },
    {
        "name": "拷贝文件或目录到目标主机",
        "copy": {
            "src": "需要copy的文件或目录 || {}",
            "dest": "需要拷贝到的目标目录 || {}",
            "mode": "0644"
        },
        "tags": [
            "install",
            "deploy"
        ]
    }
]
```
备注：数据结构中，带有'{}'的变量需要进行赋值后传入服务器端

（2）playbook 执行文件
```
- name: install erlang
  unarchive:
    src: "{{ pkg_erlang }}.tar.gz"
    dest: "{{ rabbitmq_base }}"
    keep_newer: yes
    owner: "{{ rabbitmq_user }}"
    group: "{{ rabbitmq_group }}"
  tags:
    - deploy
    - install

- name: create work dir
  file:
    dest: "{{ rabbitmq_base }}"
    state: directory
    owner: "{{ rabbitmq_user }}"
    group: "{{ rabbitmq_group }}"
  tags:
    - install
    - deploy

- name: 拷贝rabbitmq压缩包
  unarchive:
    src:  '{{ pkg_version }}.tar.gz'
    dest: "{{ rabbitmq_base }}"
    keep_newer: yes
    owner: "{{ rabbitmq_user }}"
    group: "{{ rabbitmq_group }}"
  tags:
    - install
    - deploy
```
> 由前端传入的playbook组合数据结构会生成临时playbook roles的task文件，文件结构如上所示

备注：数据结构中 '{{ }}' 的变量值来自 inventory主机清单中传入的变量

（3）playbook 任务执行
> inventory主机清单和playbook模板数据传入后，TaskServer会自动执行playbook任务，执行结果会保存到数据库中 
   

## 五、TaskServer启动执行

### 5.1 服务指令说明
```shell
$ ./taskCtl --help
Usage:
  taskCtl [command]

Available Commands:
  help        Help about any command
  startTask   启动服务端.
  stopTask    关闭远程批量操作执行器服务.

Flags:
  -h, --help   help for taskCtl

Use "taskCtl [command] --help" for more information about a command.
```

### 5.2 启动远程操作执行器
```shell
$ ./taskCtl startTask
```

### 5.3 远程操作日志查看
> 执行任务后可在日志时时查看任务进行状态，以下为示例。
```shell
$ tailf TaskServer/logs/task.log
PLAY RECAP *********************************************************************
192.168.75.165             : ok=1    changed=0    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0
192.168.75.167             : ok=2    changed=1    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0


PLAY [ssh弱密码漏洞修复] **************************************************************

PLAY [ssh弱密码漏洞修复] **************************************************************

TASK [Gathering Facts] *********************************************************
ok: [192.168.75.167]

PLAY [ssh弱密码漏洞修复] **************************************************************

TASK [Gathering Facts] *********************************************************
ok: [192.168.75.167]

TASK [sshpasspatch : 更新/etc/ssh/sshd_config弱密码口令配置:echo "ciphers aes128-ctr,aes192-ctr,aes256-ctr" >> /etc/ssh/sshd_config] ***
changed: [192.168.75.167]

TASK [sshpasspatch : 更新/etc/ssh/sshd_config弱密码口令配置:echo "macs hmac-sha1,umac-64@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-ripemd160,hmac-ripemd160@openssh.com" >> /etc/ssh/sshd_config] ***
changed: [192.168.75.167]
```

TODO:
1. 自动执行playbook任务
2. playbook模板示例编写
3. TaskServer 程序接口文档编写
4. 完善服务端与前端交互的playbook模板解析格式