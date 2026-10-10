# ADR-WEB-001: 本机浏览器 UI 与冻结引擎的边界

日期：2026-10-10。状态：已采纳。适用：`ui-test`。

## 决定

React/TypeScript/Vite 负责表现和输入，FastAPI/Uvicorn 提供同源静态文件、
HTTP 操作和 WebSocket 状态。服务只监听 loopback，拒绝外部页面 Origin；
不引入账号、公网托管、研究 worker 或原生引擎依赖。

每局由独立 UIController/DictSettingsStore 持有状态；不在前端复制合法性。
共享设置常量移至 Qt-free 模块，桌面 settings 重导出兼容旧导入。
Controller 新增 `record_text` / `load_record_text` 作为文件无关接口，
原有文件入口复用相同 replay/错误语义，后端源码和清单保持冻结。

HTTP 变更携带 revision、request_id；重复成功操作幂等，过期操作返回冲突和
最新状态。合法行动 ID 绑定 revision，并传递完整 Action，保留语义身份。
客户端仅接受同一棋局不旧于当前 revision 的状态；重连获取完整快照，
不自动重发未确认操作。变更状态通知使用有界队列，慢客户端只接收最新快照。

服务事件循环串行执行 controller 操作；全局单搜索线程读取捕获的 snapshot，
不触碰 controller。取消令牌同时由服务持有，undo/restart 清空 controller
字段后仍能否决旧 worker。新搜索等待旧 worker 真正返回；失败暂停并保留棋局。
关闭时先取消各局再等待任务并回收线程。每步保存含完整规则的续局包，临时文件
原子替换；启动后仅在玩家主动继续时恢复搜索。瞬态任务、选择和历史预览不落盘。

## 取舍

单线程搜索降低首版生命周期复杂度，适合本机小游戏；CPU/GIL 延迟以实测验收。
公网多用户未来需要独立的资源隔离与会话治理，不直接暴露当前服务。
存档保留冻结棋谱格式，不能伪造非当前行动方认输；UI 在玩家回合开放认输。
用户配置和随机种子属于 UI 续局元数据，不影响 RuleSet/Record 引擎语义。

## 保证

真实 PVE、升变/打入、棋谱往返、版本冲突、重复请求、取消后的旧结果、
导入失败保留局面、重连及服务退出通过产品/浏览器测试覆盖；冻结校验防止
UI 工作修改引擎。运行数据、构建物、截图和原始测量输出不进入 Git。
