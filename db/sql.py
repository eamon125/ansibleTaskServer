# -*- coding:utf-8 -*-

from configs import settings

def TableExistSql(name):
    return "select exists(select * from information_schema.tables where table_name='%s')" % name

def CreateTablePlayTask():
    sql = """
        DROP SEQUENCE IF EXISTS "public"."tk_play_task_id_seq";
        CREATE SEQUENCE "public"."tk_play_task_id_seq" 
        INCREMENT 1
        MINVALUE  1
        MAXVALUE 9223372036854775807
        START 1
        CACHE 1;
        
        DROP TABLE IF EXISTS "public"."tk_play_task";
        CREATE TABLE "public"."tk_play_task" (
          "id" int4 NOT NULL DEFAULT nextval('tk_play_task_id_seq'::regclass) PRIMARY KEY,
          "inventory_id" integer NOT NULL,
          "play_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "task_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "json_data" text COLLATE "pg_catalog"."default" NOT NULL,
          "status" integer NOT NULL DEFAULT(0),
          "create_time" timestamp(0)
        );
        
        ALTER TABLE "public"."tk_play_task" OWNER TO "%s";
    """ % settings.db.dbuser

    return sql


def CreateTableInventory():
    sql = """
        DROP SEQUENCE IF EXISTS "public"."tk_inventory_seq";
        CREATE SEQUENCE "public"."tk_inventory_seq" 
        INCREMENT 1
        MINVALUE  1
        MAXVALUE 9223372036854775807
        START 1
        CACHE 1;

        DROP TABLE IF EXISTS "public"."tk_inventory";
        CREATE TABLE "public"."tk_inventory" (
          "id" int4 NOT NULL DEFAULT nextval('tk_inventory_seq'::regclass) PRIMARY KEY,
          "module" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "type" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "tags" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "inventory_data" text COLLATE "pg_catalog"."default" NOT NULL,
          "create_time" timestamp(0)
        );

        ALTER TABLE "public"."tk_inventory" OWNER TO "%s";
    """ % settings.db.dbuser

    return sql

def CreateTableTaskResult():
    sql = """
        DROP SEQUENCE IF EXISTS "public"."tk_results_id_seq";
        CREATE SEQUENCE "public"."tk_results_id_seq" 
        INCREMENT 1
        MINVALUE  1
        MAXVALUE 9223372036854775807
        START 1
        CACHE 1;
        
        DROP TABLE IF EXISTS "public"."tk_results";
        CREATE TABLE "public"."tk_results" (
          "id" int4 NOT NULL DEFAULT nextval('tk_results_id_seq'::regclass) PRIMARY KEY,
          "jid" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "host" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "status" varchar(255) COLLATE "pg_catalog"."default",
          "msg" text COLLATE "pg_catalog"."default",
          "service_name" varchar(255) COLLATE "pg_catalog"."default" DEFAULT ''::character varying,
          "create_time" timestamp(0),
          "update_time" timestamp(0)
        );
        
        ALTER TABLE "public"."tk_results" OWNER TO "%s";
    """ % settings.db.dbuser
    return sql

def CreateTableTaskJob():
    sql = """
        DROP SEQUENCE IF EXISTS "public"."tk_jobs_id_seq";
        CREATE SEQUENCE "public"."tk_jobs_id_seq" 
        INCREMENT 1
        MINVALUE  1
        MAXVALUE 9223372036854775807
        START 1
        CACHE 1;
        
        DROP TABLE IF EXISTS "public"."tk_jobs";
        CREATE TABLE "public"."tk_jobs" (
          "id" int4 NOT NULL DEFAULT nextval('tk_jobs_id_seq'::regclass) PRIMARY KEY,
          "jid" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "host" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
          "status" varchar(255) COLLATE "pg_catalog"."default",
          "msg" text COLLATE "pg_catalog"."default",
          "task" varchar(255) COLLATE "pg_catalog"."default" NOT NULL DEFAULT ''::character varying,
          "service_name" varchar(255) COLLATE "pg_catalog"."default" DEFAULT ''::character varying,
          "create_time" timestamp(0),
          "update_time" timestamp(0)
        );
        
        ALTER TABLE "public"."tk_jobs" OWNER TO "%s";
    """ % settings.db.dbuser
    return sql