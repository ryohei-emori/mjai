# MJAI デプロイガイド

## クイックスタート

### ローカルからのデプロイ

1. **terraform.tfvarsの作成**
   ```bash
   cd terraform
   cp terraform.tfvars.example terraform.tfvars
   # terraform.tfvarsを編集して実際の値を設定
   ```

2. **デプロイ実行**
   ```bash
   ./deploy-local.sh
   ```

3. **確認**
   - Backend: https://mjai-backend.onrender.com/health
   - Frontend: https://mjai-frontend.onrender.com

### GitHub Actionsでの自動デプロイ

1. **GitHub Secretsの設定**
   - `RENDER_API_KEY`
   - `DATABASE_URL`
   - `GEMINI_API_KEY`
   - `GEMINI_MODEL`

2. **mainブランチにpush**
   ```bash
   git push origin main
   ```

3. **GitHub Actionsで確認**
   - Actions → Deploy to Render

## 詳細は以下を参照

- [デプロイ計画書](./deployment-plan.md)
- [Terraform README](../terraform/README.md)
