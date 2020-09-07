package configs

import (
	"fmt"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"gopkg.in/natefinch/lumberjack.v2"
	"os"
	"path"
	"time"
	"TaskServer1/utils"
)

// 日志
var Logger *zap.SugaredLogger

func LogLevel() map[string]zapcore.Level {
	level := make(map[string]zapcore.Level)
	level["debug"] = zap.DebugLevel
	level["info"] = zap.InfoLevel
	level["warn"] = zap.WarnLevel
	level["error"] = zap.ErrorLevel
	level["dpanic"] = zap.DPanicLevel
	level["panic"] = zap.PanicLevel
	level["fatal"] = zap.FatalLevel
	return level
}

var PlaybookPath string
var TaskAddr string

type TaskConf struct {
	OS int
	LogFile string
}

var TaskServer *TaskConf

func InitConfig() {
	// 解析配置文件
	cfg := ParserConfig()

	// 日志配置
	logLevelOpt := cfg.MustValue("logging", "level")  // 日志级别
	levelMap := LogLevel()
	logLevel, _ := levelMap[logLevelOpt]
	atomicLevel := zap.NewAtomicLevelAt(logLevel)

	encodingConfig := zapcore.EncoderConfig{
		TimeKey: cfg.MustValue("logging", "encoder_config_time_key"),
		LevelKey: cfg.MustValue("logging", "encoder_config_level_key"),
		NameKey: cfg.MustValue("logging", "encoder_config_name_key"),
		CallerKey: cfg.MustValue("logging", "encoder_config_caller_key"),
		MessageKey: cfg.MustValue("logging", "encoder_config_msg_key"),
		StacktraceKey: cfg.MustValue("logging", "encoder_config_trace_key"),
		LineEnding: zapcore.DefaultLineEnding,
		EncodeLevel: zapcore.LowercaseLevelEncoder,
		EncodeTime: func(t time.Time, enc zapcore.PrimitiveArrayEncoder) {
			enc.AppendString(t.Format("2006-01-02 15:04:05"))
		},
		EncodeDuration: zapcore.SecondsDurationEncoder,
		EncodeCaller: zapcore.FullCallerEncoder,
	}

	// 初始化字段
	filedKey := cfg.MustValue("logging", "initial_fields_key")
	fieldValue := cfg.MustValue("logging", "initial_fields_value")
	filed := zap.Fields(zap.String(filedKey, fieldValue))

	// 是否开启日志滚动
	isRotate := cfg.MustBool("logging", "enable_rotate")
	if isRotate {
		rotateFile := cfg.MustValue("logging", "rotate_file")
		writer := zapcore.AddSync(&lumberjack.Logger{
			Filename:   rotateFile,
			MaxSize:    cfg.MustInt("logging", "rotate_max_size"),
			MaxBackups: cfg.MustInt("logging", "rotate_max_backups"),
			MaxAge:     cfg.MustInt("logging", "rotate_max_age"),
			Compress:   cfg.MustBool("logging", "rotate_compress"),
		})
		var core zapcore.Core
		// 是否在日志切割开启的情况下开启console打印
		rotateConsole := cfg.MustBool("logging", "rotate_console")
		if rotateConsole {
			consoleDebugging := zapcore.Lock(os.Stdout)
			// 多个core使用NewTee
			core = zapcore.NewTee(
				zapcore.NewCore(
					zapcore.NewJSONEncoder(encodingConfig),
					writer,
					logLevel,),
				zapcore.NewCore(
					zapcore.NewJSONEncoder(encodingConfig),
					consoleDebugging,
					logLevel,
				),
			)
		} else {
			core = zapcore.NewCore(
					zapcore.NewJSONEncoder(encodingConfig),
					writer,
					logLevel,)
		}

		disableStacktrace := cfg.MustBool("logging", "disable_stacktrace")
		if !cfg.MustBool("logging", "disable_caller") {
			caller := zap.AddCaller()

			if !disableStacktrace {
				stacktrace := zap.AddStacktrace(logLevel)
				Logger = zap.New(core, caller, stacktrace, filed).Sugar()
			} else {
				Logger = zap.New(core, caller, filed).Sugar()
			}
		} else {
			if !disableStacktrace {
				stacktrace := zap.AddStacktrace(logLevel)
				Logger = zap.New(core, stacktrace, filed).Sugar()
			} else {
				Logger = zap.New(core, filed).Sugar()
			}
		}
	} else {
		logCfg := zap.Config{
			Level: atomicLevel,
			Development: cfg.MustBool("logging", "development"),
			DisableCaller: cfg.MustBool("logging", "disable_caller"),
			DisableStacktrace: cfg.MustBool("logging", "disable_stacktrace"),
			Encoding: cfg.MustValue("logging", "encoding"),
			EncoderConfig: encodingConfig,
			InitialFields: map[string]interface{}{filedKey: fieldValue},
			OutputPaths: cfg.MustValueArray("logging", "output_paths", ","),
			ErrorOutputPaths: cfg.MustValueArray("logging", "error_output_paths", ","),
		}

		logger, err := logCfg.Build()
		if err != nil {
			panic(fmt.Sprintf("Loggger初始化失败: %v", err))
		}

		Logger = logger.Sugar()
	}

	// ansible 执行器配置
	TaskServer = &TaskConf{
		OS:cfg.MustInt("server", "os"),
		LogFile:path.Join(utils.AbsPath(), cfg.MustValue("server", "log_file")),
	}

	// Playbook
	PlaybookPath = cfg.MustValue("play", "playbook_path")

	// task
	TaskAddr = cfg.MustValue("server","addr")
}
