# LabInstru – Django

Projeto Django que converte seu app Streamlit em páginas Django.

## Como rodar

```bash
cd labinstru_site
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8077
```

## Variáveis de ambiente

Defina antes de rodar (opcional para recursos externos):

- `GEMINI_API_KEY` — chave da API do Gemini (chat ZEUS)
- `PURPLEAIR_API_KEY` — chave da PurpleAir
- `SUPABASE_URL` e `SUPABASE_KEY` — para buscar dados reais da rede HOBO

No Linux/macOS:
```bash
export GEMINI_API_KEY="sua_chave"
export PURPLEAIR_API_KEY="sua_chave"
export SUPABASE_URL="https://xxxxxxxx.supabase.co"
export SUPABASE_KEY="eyJ..."
```

## Onde editar

- Navegação e layout: `siteapp/templates/siteapp/base.html` e `static/styles.css`
- Páginas: `siteapp/templates/siteapp/*.html`
- Lógica: `siteapp/views.py`

## Observações

- As imagens em `static/` são placeholders vazios. Substitua pelos arquivos reais.
- Se não configurar Supabase, a página "Rede de Estações HOBO" usa dados simulados apenas para visualização.
```

