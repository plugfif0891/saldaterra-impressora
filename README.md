# 🖨 Saldaterra Impressora

App Android para imprimir comandas automaticamente via Bluetooth  
Impressora: **Kapbom KA-1444** | Banco: **Supabase** | 2° plano ativo

---

## ✅ Pré-requisitos antes de tudo

1. **Pareie a impressora KA-1444 no Bluetooth do celular**  
   Configurações do Android → Bluetooth → Parear novo dispositivo → selecione "KA-1444"

2. **No Supabase**, execute esse SQL se ainda não tiver a coluna:
   ```sql
   ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS impresso BOOLEAN DEFAULT FALSE;
   ```

---

## 🚀 Como gerar o APK via GitHub Actions

### Passo 1 — Criar repositório no GitHub
1. Acesse https://github.com/new
2. Nome: `saldaterra-impressora`
3. Visibilidade: **Privado** (recomendado)
4. Clique em **Create repository**

### Passo 2 — Enviar os arquivos
No terminal do seu computador:
```bash
git init
git add .
git commit -m "primeiro commit"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/saldaterra-impressora.git
git push -u origin main
```

### Passo 3 — Aguardar a compilação
1. Acesse seu repositório no GitHub
2. Clique na aba **Actions**
3. Clique no workflow "Compilar APK Saldaterra"
4. Aguarde ~15-25 minutos (primeira vez baixa NDK/SDK)
5. Quando terminar, clique em **Artifacts** → baixe o APK

### Passo 4 — Instalar no celular
1. Copie o .apk para o celular (WhatsApp, cabo USB, Google Drive)
2. Ative "Instalar apps de fontes desconhecidas" nas configurações
3. Abra o arquivo .apk e instale

---

## 📱 Como usar o app

1. Abra o app → clique em **📡 Buscar**
2. Selecione a impressora **KA-1444**
3. Clique em **🖨 Imprimir Teste** para confirmar que está funcionando
4. Clique em **▶ INICIAR MONITORAMENTO**
5. **Minimize o app** — ele continua rodando em 2° plano! ✅

A notificação "Saldaterra - Monitorando" aparece na barra do Android.  
Enquanto ela estiver visível, o app está ativo.

---

## 🔧 Coluna no Supabase obrigatória

A tabela `pedidos` precisa ter:
- Coluna `status` com valor `'novo'` para pedidos novos
- Coluna `impresso` do tipo `BOOLEAN` com padrão `FALSE`

Pedidos com `status='novo'` e `impresso=false` serão impressos automaticamente.  
Após imprimir, o app muda `impresso` para `true` para não reimprimir.
