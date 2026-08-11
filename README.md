# chase-csv-summarizer

信用卡／銀行帳戶 CSV 對帳單彙整工具 (Credit Card & Bank Account CSV Summarizer)

一個以 React + Vite 打造的網頁小工具，讓你上傳信用卡或銀行帳戶匯出的 CSV 對帳單，快速產生消費彙整報表（分類、月度統計等），協助個人記帳與財務追蹤。

🔗 線上測試網址

專案已透過 GitHub Actions 自動部署到 GitHub Pages，無需安裝任何東西即可直接體驗：

👉 https://michellewang422-eng.github.io/credit-card-bank-account-csv-summarizer/

⚠️ 若上方連結尚未開通，請確認 repo 的 Settings → Pages 中，Source 是否已設定為 gh-pages 分支（或 GitHub Actions 部署工作流程），部署完成後即可透過此網址存取。

✨ 功能特色
支援上傳信用卡 / 銀行帳戶匯出的 CSV 檔案
自動解析交易資料（日期、商家、金額等欄位）
依分類或月份彙整消費統計
純前端處理，資料不會上傳到任何伺服器，保護個人財務隱私
部署於 GitHub Pages，開啟網址即可使用，無需登入或安裝
🚀 如何使用（給一般使用者）
開啟線上測試網址：https://michellewang422-eng.github.io/credit-card-bank-account-csv-summarizer/
點選頁面上的「上傳 CSV」按鈕，選擇你從信用卡或銀行網站匯出的 CSV 對帳單檔案
系統會自動解析檔案內容，顯示交易明細與彙整結果
依需求切換檢視方式（例如：依分類、依月份）查看統計圖表或表格
若要分析多份對帳單，可重複上傳多個 CSV 檔案

💡 小提醒：不同銀行 / 信用卡公司匯出的 CSV 欄位格式可能不同，若解析結果不正確，請確認欄位名稱（日期、金額、商家說明等）是否與工具預期的格式一致。

🛠️ 本地開發（給想改程式碼的人）

如果想在本機執行或修改此專案：

bash
# 1. 複製專案
git clone https://github.com/michellewang422-eng/credit-card-bank-account-csv-summarizer.git
cd credit-card-bank-account-csv-summarizer

# 2. 安裝套件
npm install

# 3. 啟動本地開發伺服器
npm run dev

啟動後，依終端機提示於瀏覽器開啟（通常是 http://localhost:5173）。

建置正式版本
bash
npm run build

建置完成的靜態檔案會輸出到 dist/ 資料夾。

📦 技術棧
框架：React + Vite
部署：GitHub Actions → GitHub Pages
語言：JavaScript / TypeScript（依實際專案調整）
📁 專案結構（範例，請依實際情況調整）
credit-card-bank-account-csv-summarizer/
├── src/              # 原始碼
├── public/           # 靜態資源
├── .github/workflows/# GitHub Actions 自動部署設定
├── package.json
└── README.md
🔒 隱私聲明

本工具的 CSV 解析與彙整邏輯皆在瀏覽器端（前端）完成，不會將你的對帳單資料上傳到任何後端伺服器，可放心用於個人財務資料測試。

📄 授權

（依你的實際授權方式填寫，例如 MIT License）
