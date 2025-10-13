# /chatid 命令测试指南

## 测试前准备

### 1. 确保主进程已停止
```powershell
ch stop
```

### 2. 查看当前代码变更
```powershell
git status
git diff src/util.py
git diff src/telegram_bot.py
```

### 3. 启动主进程
```powershell
ch start
```

### 4. 查看日志确认命令已注册
```powershell
ch logs bot
```

应该能看到类似：
```
✅ 已注册命令: /addchannel, /chatid
```

## 测试场景

### 场景 1：在私有频道中测试（最重要）

1. **准备私有频道**
   - 打开一个你管理的私有 Telegram 频道
   - 确保你的 Bot 已被添加为管理员

2. **发送命令**
   - 在频道中输入：`/chatid`
   - 发送

3. **验证回复**
   
   Bot 应该立即回复：
   ```
   📍 频道信息
   
   💬 Chat ID: `-1001234567890`
   📂 类型: supergroup
   📌 标题: [你的频道名称]
   
   💡 提示：复制上面的 Chat ID 到配置文件中使用
   ```

4. **检查日志**
   ```powershell
   ch logs bot | Select-String "chatid"
   ```
   
   应该看到：
   ```
   📍 /chatid 命令 - Chat ID: -1001234567890, 类型: supergroup, 标题: [你的频道名称]
   ```

5. **验证 Chat ID**
   - 复制显示的 Chat ID
   - 尝试在 `config.yaml` 中使用它
   - 或者发送一条测试消息验证

### 场景 2：在与 Bot 的私聊中测试

1. **打开与 Bot 的私聊**
   - 在 Telegram 中找到你的 Bot
   - 点击进入聊天

2. **发送命令**
   - 输入：`/chatid`
   - 发送

3. **验证回复**
   
   Bot 应该回复：
   ```
   📍 频道信息
   
   💬 Chat ID: `123456789`
   📂 类型: private
   👤 用户: [你的名字] (@你的用户名)
   
   💡 提示：复制上面的 Chat ID 到配置文件中使用
   ```

### 场景 3：在公开频道中测试

1. **准备公开频道**（如果有）
   - 打开你管理的公开频道
   - 确保 Bot 已添加

2. **发送命令**
   - 输入：`/chatid`

3. **验证回复**
   - 应该显示该频道的 Chat ID
   - 类型应该是 `channel` 或 `supergroup`

### 场景 4：在普通群组中测试

1. **准备测试群组**
   - 创建或使用现有的 Telegram 群组
   - 邀请 Bot 加入

2. **发送命令**
   - 输入：`/chatid`

3. **验证回复**
   - 应该显示群组的 Chat ID
   - 类型应该是 `group` 或 `supergroup`

## 错误处理测试

### 测试 1：Bot 无发送权限

1. 将 Bot 添加到频道，但不给发送消息权限
2. 发送 `/chatid`
3. **预期结果**：命令无法执行（Bot 无法回复）

### 测试 2：主进程未启动

1. 停止主进程：`ch stop`
2. 在频道中发送 `/chatid`
3. **预期结果**：Bot 无响应
4. 重新启动：`ch start`
5. 再次发送 `/chatid`
6. **预期结果**：正常工作

## 集成测试：配置新频道完整流程

### 完整配置流程测试

1. **创建新的测试频道**
   - 在 Telegram 中创建一个新频道（私有）
   - 邀请你的 Bot 加入

2. **获取 Chat ID**
   - 在频道中发送：`/chatid`
   - 复制 Bot 回复的 Chat ID（例如：`-1001234567890`）

3. **添加到配置文件**
   - 打开 `config/config.yaml`
   - 添加新的频道组：
   
   ```yaml
   channel_groups:
     # ... 现有配置 ...
     
     - name: "测试频道"
       telegram_chat_id: "-1001234567890"  # 使用刚才获取的 ID
       audio_folder: "au/test"
       enabled: true
       youtube_channels:
         - "@example_channel"
   ```

4. **重启主进程**
   ```powershell
   ch restart
   ```

5. **验证配置**
   - 查看日志确认新频道组已加载：
   ```powershell
   ch logs bot | Select-String "测试频道"
   ```
   
   - 应该看到：
   ```
   📤 已配置发送任务: 测试频道 -> -1001234567890
   ```

6. **测试发送**
   - 等待 Bot 自动发送，或手动触发
   - 验证新频道能正常接收文件

## 性能测试

### 测试高频使用

1. 在同一频道中连续发送 5 次 `/chatid`
2. **验证**：
   - 所有请求都应该正常响应
   - 响应时间应该稳定（< 1 秒）
   - 日志中应该有 5 条记录

### 测试多频道并发

1. 在 3-5 个不同频道中同时发送 `/chatid`
2. **验证**：
   - 所有频道都应该收到正确的回复
   - 每个回复都应该显示正确的 Chat ID
   - 不同频道的 Chat ID 应该不同

## 日志验证

### 检查日志格式

```powershell
# 查看最近的 chatid 命令日志
ch logs bot | Select-String "chatid"

# 使用 jq 查看 JSONL 格式
jq 'select(.message | contains("chatid"))' logs/bot.log
```

### 预期日志格式

```json
{
  "timestamp": "2025-10-13T10:30:45",
  "level": "INFO",
  "component": "bot",
  "message": "📍 /chatid 命令 - Chat ID: -1001234567890, 类型: supergroup, 标题: 我的测试频道"
}
```

## 常见问题排查

### 问题 1：Bot 不响应

**可能原因**：
1. 主进程未启动
2. Bot 没有发送消息权限
3. Bot 未加入频道

**排查步骤**：
```powershell
# 检查进程状态
ch status

# 查看最近的错误日志
ch logs error

# 查看 bot 日志
ch logs bot -f
```

### 问题 2：回复消息格式错误

**可能原因**：
- Markdown 解析错误

**排查步骤**：
```powershell
# 查看详细错误
ch logs bot | Select-String "chatid" | Select-Object -Last 10
```

### 问题 3：Chat ID 显示为空

**不太可能发生**，但如果出现：
```powershell
# 查看完整日志
ch logs bot --lines 100
```

## 回归测试

### 确保现有功能不受影响

1. **测试 /addchannel 命令**
   ```
   /addchannel @test_channel
   ```
   应该正常工作

2. **测试文件发送功能**
   - 等待自动发送任务
   - 或手动触发发送
   - 验证文件正常发送

3. **测试下载功能**
   - 检查下载日志
   - 验证音频正常下载

## 测试检查清单

完成以下所有项目即算测试通过：

- [ ] 主进程能正常启动
- [ ] 启动日志显示命令已注册
- [ ] 在私有频道中能正常使用 `/chatid`
- [ ] 在私聊中能正常使用 `/chatid`
- [ ] Bot 回复消息格式正确
- [ ] Chat ID 显示正确
- [ ] 日志记录正确
- [ ] 能用获取的 Chat ID 成功配置新频道
- [ ] `/addchannel` 命令仍正常工作
- [ ] 文件发送功能正常
- [ ] 下载功能正常

## 测试报告模板

```
## /chatid 命令测试报告

**测试日期**：2025-10-13
**测试人员**：[你的名字]
**版本**：[commit hash]

### 测试环境
- 操作系统：Windows 10
- PowerShell 版本：7.x
- Python 版本：3.x

### 测试结果

#### 基础功能测试
- [ ] 私有频道：✅ 通过 / ❌ 失败
- [ ] 私聊：✅ 通过 / ❌ 失败
- [ ] 公开频道：✅ 通过 / ❌ 失败
- [ ] 普通群组：✅ 通过 / ❌ 失败

#### 集成测试
- [ ] 完整配置流程：✅ 通过 / ❌ 失败

#### 回归测试
- [ ] /addchannel 命令：✅ 通过 / ❌ 失败
- [ ] 文件发送：✅ 通过 / ❌ 失败
- [ ] 下载功能：✅ 通过 / ❌ 失败

### 发现的问题
[如有问题，在此列出]

### 总体评估
✅ 所有测试通过，可以投入使用
或
❌ 存在问题，需要修复

### 备注
[其他需要说明的内容]
```

## 自动化测试脚本（可选）

如果需要，可以创建自动化测试脚本：

```powershell
# test-chatid.ps1
Write-Host "开始测试 /chatid 命令..."

# 1. 检查主进程
Write-Host "`n检查主进程状态..."
.\ch status

# 2. 检查日志中的命令注册
Write-Host "`n检查命令注册..."
Get-Content logs\bot.log -Tail 50 | Select-String "已注册命令"

# 3. 提示手动测试
Write-Host "`n请手动完成以下测试："
Write-Host "1. 在测试频道中发送 /chatid"
Write-Host "2. 验证 Bot 回复"
Write-Host "3. 检查 Chat ID 是否正确"
Write-Host "`n完成后按任意键继续..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 4. 查看相关日志
Write-Host "`n最近的 chatid 日志："
Get-Content logs\bot.log | Select-String "chatid" | Select-Object -Last 5

Write-Host "`n测试完成！"
```

运行：
```powershell
.\test-chatid.ps1
```

