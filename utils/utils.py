import psycopg2

from configs import settings


def excPgSql(sql):
    newCon = psycopg2.connect(dbname=settings.db.dbname, user=settings.db.dbuser,
        password=str(settings.db.dbpass), host=settings.db.dbhost, port=str(settings.db.dbport))
    cur = newCon.cursor()
    try:
        cur.execute(sql)
    except:
        import traceback
        traceback.print_exc()
    else:
        print("o.....k")
    #result = cur.fetchall()
    newCon.commit()
    cur.close()
    newCon.close()

def queryPgSql(sql):
    newCon = psycopg2.connect(dbname=settings.db.dbname, user=settings.db.dbuser,
        password=str(settings.db.dbpass), host=settings.db.dbhost, port=str(settings.db.dbport))
    cur = newCon.cursor()
    try:
        cur.execute(sql)
    except:
        import traceback
        traceback.print_exc()
    result = cur.fetchall()
    cur.close()
    newCon.close()
    return result
