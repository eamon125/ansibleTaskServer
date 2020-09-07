package utils

import (
	"errors"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// 获取当前操作路径的目录
func AbsPath() string {
	file, err := exec.LookPath(os.Args[0])
	if err != nil {
		return ""
	}
	path, err := filepath.Abs(file)
	if err != nil {
		return ""
	}
	i := strings.LastIndex(path, "/")
	if i < 0 {
		i = strings.LastIndex(path, "\\")
	}
	if i < 0 {
		panic(errors.New(`error: Can't find "/" or "\".`))
		return ""
	}
	return string(path[0 : i+1])
}

// 获取当前时间
func CurrentTime() string {
	return time.Now().Format("2006-01-02 15:04:05")
}
