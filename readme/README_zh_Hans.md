# 通用媒体 API

这是一个可配置的 Dify 工具插件，用于将不同厂商的图片、视频生成 API
接入工作流，支持同步 JSON 接口以及异步提交和轮询接口。

## 主要功能

- 同步图片或视频生成
- 异步任务提交、状态轮询和结果下载
- Bearer、原始 API Key 和固定请求头
- 支持原始 JSON 类型的递归请求模板
- `$.data[0].url` 形式的响应路径
- URL 和 Base64 媒体响应
- 输出 Dify 文件供后续节点使用

## 配置原则

Provider 的 API 基础地址必须是公网 HTTPS 地址。工具节点中的接口路径必须
是该主机下的相对路径。插件会拒绝 HTTP、localhost、私有网络地址、URL 内
嵌凭据和跨域 API 重定向。

请求模板可使用 `{{prompt}}`、`{{model}}`、`{{input_url}}`、
`{{parameters.xxx}}`；异步状态配置还可使用 `{{task_id}}`。

完整字段解释、同步与异步示例、安全说明及开发命令请参阅根目录英文
[README](../README.md)。
