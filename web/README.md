# HRAI-GO · Observatório (site estático)

Site independente: participação ao vivo por QR code, telão com agregados, base de conhecimento e monitoramento.
Sem CDN de terceiros (bibliotecas, three.js r128 e fontes ficam em `vendor/` e `fonts/`; licenças em `vendor/LICENCAS.md`).

Visual: tema `camara` do design system v2 (`design-system/docs/07-camara.md`). `assets/tokens.css` é **gerado**:
`python3 design-system/scripts/export_css.py camara web/assets/tokens.css`. Dados do modelo brasileiro em
`assets/modelo.js` (os mesmos do protótipo 3D); conteúdo editável em `assets/conteudo.js`.

## Rotas
- `#participar`: fluxo de 5 passos no celular (anônimo).
- `#ao-vivo`: telão para projeção (QR code, contagem, agregados, simulação de reserva).
- `#conhecimento` (começa pelo modelo brasileiro: 22 componentes e cobertura das 28 áreas) e `#monitoramento`: acesso individual.
- `camara/`: tour 3D do Shadow Council, com alternativa sem WebGL.
A sala vem do parâmetro `?sala=`; o QR code já inclui a sala.

## Publicar
1. **Supabase**: criar projeto (região São Paulo, `sa-east-1`), rodar `supabase/migrations/20261117000000_respostas_demo.sql` no SQL Editor e ativar *Authentication > Sign In / Providers > Allow anonymous sign-ins*.
2. **Variáveis do repositório** (Settings > Secrets and variables > Actions > *Variables*): `SUPABASE_URL` e `SUPABASE_ANON_KEY` (a chave anon é pública por desenho; a segurança vem das políticas RLS).
3. **GitHub Pages**: Settings > Pages > Source: *GitHub Actions*. Se o ambiente `github-pages` só permitir a branch padrão, incluir `claude/awesome-planck-wvuayj` em Settings > Environments > github-pages, ou fazer merge na `main`.
4. O workflow `.github/workflows/pages.yml` gera `config.js` e publica a pasta `web/` a cada push.

Sem as variáveis, o site roda em modo local (ensaio entre abas do mesmo navegador).

## Ensaio local
`python3 -m http.server 8765 --directory web` e abrir `http://localhost:8765/#ao-vivo`.
