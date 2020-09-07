import psycopg2
from configs import settings
from db import sql

db_name = settings.db.dbname
db_host = settings.db.dbhost
db_pass = settings.db.dbpass
db_user = settings.db.dbuser
db_port = settings.db.dbport

def initDB():
    newCon = psycopg2.connect(dbname=db_name, user=db_user,
        password=str(db_pass), host=db_host, port=str(db_port))

    cur = newCon.cursor()

    # 判断tk_results表是否存在
    if TableIsExist(sql.TableExistSql("tk_results"), cur):
        print("table [ tk_results ] is existed!")
    else:
        try:
            cur.execute(sql.CreateTableTaskResult())
        except:
            import traceback
            traceback.print_exc()

        newCon.commit()
        print('Table [tk_results] created successfully!')

    # 判断tk_jobs表是否存在
    if TableIsExist(sql.TableExistSql("tk_jobs"), cur):
        print("table [ tk_jobs ] is existed!")
    else:
        try:
            cur.execute(sql.CreateTableTaskJob())
        except:
            import traceback
            traceback.print_exc()

        newCon.commit()
        print('Table [tk_jobs] created successfully!')

    # 判断tk_play_task表是否存在
    if TableIsExist(sql.TableExistSql("tk_play_task"), cur):
        print("table [ tk_play_task ] is existed!")
    else:
        try:
            cur.execute(sql.CreateTablePlayTask())
        except:
            import traceback
            traceback.print_exc()

        newCon.commit()
        print('Table [tk_play_task] created successfully!')

    # 判断tk_inventory表是否存在
    if TableIsExist(sql.TableExistSql("tk_inventory"), cur):
        print("table [ tk_inventory ] is existed!")
    else:
        try:
            cur.execute(sql.CreateTableInventory())
        except:
            import traceback
            traceback.print_exc()

        newCon.commit()
        print('Table [tk_inventory] created successfully!')

    cur.close()
    newCon.close()

def TableIsExist(sqlStr, cur):
    cur.execute(sqlStr)
    result = cur.fetchone()[0]
    return result

def ExecuteSql(sqlStr):
    newCon = psycopg2.connect(dbname=db_name, user=db_user,
                              password=str(db_pass), host=db_host, port=str(db_port))

    cur = newCon.cursor()
    result = True
    code = 200
    try:
        cur.execute(sqlStr)
    except:
        code = 400
        result = "sql control error"

    newCon.commit()
    cur.close()
    newCon.close()
    return code, result


