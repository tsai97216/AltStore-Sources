# Chi Sources TODO

## 架構融合
- [ ] 研究 AltGallery / AltGen 的設定檔、Provider、版本解析與 merge 機制
- [x] 將 App 定義逐步從 update_source.py 抽離成獨立設定
- [x] 抽象 GitHub、AltSource、AppTesters 等來源 Provider
- [ ] 保留現有的特殊 App 解析、IPA 驗證、Retry 與舊版本 fallback
- [ ] 加入單一 App 更新能力，避免每次都完整重跑

## 可靠性
- [x] 補齊 update_source.py 的狀態判定測試
- [ ] 檢查並強化 AltStore Source schema 驗證
- [ ] 檢查各來源失敗時的 fallback 行為
- [ ] 檢查版本、IPA asset 與檔案大小判定的邊界情況

## CI / 維護
- [ ] 檢查 GitHub Actions 的更新流程與提交條件
- [ ] 確認自動更新不會因單一 App 失敗而破壞整個 Source
- [ ] 評估更新頻率、API 使用量與不必要的請求

## README / Source
- [ ] 保留並完善更新狀態資訊
- [ ] 評估加入 News / 更新紀錄
- [ ] 檢查 Source metadata、featuredApps 與 App metadata

## 最後檢核
- [ ] Python 編譯
- [ ] pytest
- [ ] JSON 驗證
- [ ] AltStore Source 驗證
- [ ] 實際執行 update_source.py
- [ ] 檢查 git diff / commit 結果
