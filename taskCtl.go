package main

import (
	"TaskServer/configs"
	"TaskServer/utils"
	"fmt"
	"github.com/spf13/cobra"
	"go.uber.org/zap"
	"go.uber.org/zap/zapcore"
	"io/ioutil"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
)

var (
	cmd    *exec.Cmd
	output []byte
	err    error
)

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

func main() {
	// 初始化配置
	configs.InitConfig()

	var rootCmd = &cobra.Command{Use: "taskCtl"}

	// TODO: Python程序的状态检查指令操作
	var cmdStartTask = &cobra.Command{
		Use:   "startTask",
		Short: "启动远程批量操作执行器服务.",
		Long:  `启动远程批量操作执行器服务.`,
		Run: func(cmd *cobra.Command, args []string) {
			StartTask()
		},
	}

	var cmdSopTask = &cobra.Command{
		Use:   "stopTask",
		Short: "关闭远程批量操作执行器服务.",
		Long: `关闭远程批量操作执行器服务.
`,
		Run: func(cmd *cobra.Command, args []string) {
			StopTask()
		},
	}

	rootCmd.AddCommand(cmdStartTask)
	rootCmd.AddCommand(cmdSopTask)
	err := rootCmd.Execute()
	if err != nil {
		configs.Logger.Error(err)
	}

}

func StopGPid(pid int32, name string) {
	//p, _ := process.NewProcess(pid)
	err = syscall.Kill(-int(pid), syscall.SIGKILL)
	if err != nil {
		configs.Logger.Error(err)
	} else {
		configs.Logger.Infof("PassManager [%s] 已停止！", name)
	}
}

func StopTask() {
	pidFile := path.Join(utils.AbsPath(), "tmp/task.gpid")
	if PathExist(pidFile) {
		pidStr := strings.Trim(ReadFile(pidFile), "\n")
		pid, err := strconv.ParseInt(pidStr, 10, 32)
		if err != nil {
			Logger.Error(err)
		} else {
			// 杀死进程组
			StopGPid(int32(pid), "PassManager")
		}
	} else {
		Logger.Warnf("TaskServer进程不存在！")
	}
}

func StartTask() {
	// 启动ansible执行器
	osVersion := configs.TaskServer.OS
	logFile := configs.TaskServer.LogFile
	pythonPath := path.Join(utils.AbsPath(), "packages/miniconda3/bin/python")
	startCmd := "nohup " + pythonPath + " main.py" + " >>" + logFile + " 2>&1 &"

	ansibleCmd := exec.Command("sh", "-c", startCmd)
	stdout, err4 := ansibleCmd.StdoutPipe()
	ansibleCmd.Stderr = ansibleCmd.Stdout
	if err4 != nil {
		configs.Logger.Error(err4)
	}

	glibc214 := filepath.Join(utils.AbsPath(), "packages/glibc-2.14/lib")

	if osVersion == 6 {
		sshpass := filepath.Join(utils.AbsPath(), "packages/sshpass-rh6")
		ansibleCmd.Env = append(ansibleCmd.Env, "PATH="+os.Getenv("PATH")+":"+sshpass+"/bin")
		ansibleCmd.Env = append(ansibleCmd.Env, "LD_LIBRARY_PATH="+glibc214)
	} else {
		sshpass := filepath.Join(utils.AbsPath(), "packages/sshpass-rh7")
		ansibleCmd.Env = append(ansibleCmd.Env, "PATH="+os.Getenv("PATH")+":"+sshpass+"/bin")
	}

	// 设置进程组
	ansibleCmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	if err = ansibleCmd.Start(); err != nil {
		configs.Logger.Error(err)
	}
	// 启动成功后保存gpid文件
	f, err2 := os.OpenFile(path.Join(utils.AbsPath(), "tmp/task.gpid"), os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0600)
	defer f.Close()
	if err2 != nil {
		configs.Logger.Error(err2)
	} else {
		_, err2 = f.Write([]byte(strconv.Itoa(ansibleCmd.Process.Pid)))
		if err2 != nil {
			// sugar.Error(err2)
			configs.Logger.Panic(err2)
		}
	}

	for {
		tmp := make([]byte, 1024)
		_, err5 := stdout.Read(tmp)
		fmt.Print(string(tmp))
		if err5 != nil {
			break
		}
	}
	err6 := ansibleCmd.Wait()
	if err6 != nil {
		configs.Logger.Error(err6)
	}

	configs.Logger.Info("+++++++++++TaskServer启动完毕！+++++++++++")
}

func PathExist(_path string) bool {
	_, err := os.Stat(_path)
	if err != nil && os.IsNotExist(err) {
		return false
	}
	return true
}

func ReadFile(file string) string {
	bytes,err := ioutil.ReadFile(file)
	if err != nil {
		configs.Logger.Fatal(err)
	}
	return string(bytes)
}
