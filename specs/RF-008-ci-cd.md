# RF-008 — Entrega contínua verificável

Status: Implementado

## Objetivo

Entregar uma única cadeia auditável para validar cada mudança, testar a composição executável, publicar imagens imutáveis e implantar em staging ou produção com proteção de ambiente e rollback.

## Escopo

- Unificar os workflows de CI existentes.
- Executar `make verify` e um smoke test do Compose antes da publicação.
- Publicar backend e frontend no GHCR com SBOM, proveniência e atestação.
- Implantar somente referências por digest através de SSH com host conhecido.
- Manter configuração secreta apenas no servidor.
- Cobrir os contratos de entrega e o comportamento de rollback com testes unitários.
- Documentar bootstrap, promoção, diagnóstico, backup e rollback.

## Critérios de aceite

- [x] Pull requests não recebem permissão de escrita em packages e nunca implantam.
- [x] Publicação depende dos gates de qualidade e integração Docker.
- [x] Actions de terceiros estão fixadas por SHA completo e recebem atualização pelo Dependabot.
- [x] Imagens publicadas possuem SBOM, proveniência, atestação e referência imutável de saída.
- [x] Com `DEPLOY_ENABLED=true`, push na branch padrão promove staging e tag `v*` solicita promoção de produção.
- [x] Sem configuração explícita de deploy, o pipeline público valida e publica sem tentar acessar servidores inexistentes.
- [x] O environment do GitHub pode exigir revisão humana antes de produção.
- [x] SSH verifica `known_hosts` previamente configurado.
- [x] O Compose de produção não contém `build`, não expõe diretamente a API e exige segredos.
- [x] Uma falha de atualização restaura os digests anteriores sem remover volumes.
- [x] Smoke tests verificam interface, prontidão da API e catálogo de perfis.
- [x] Testes unitários exercitam pinagem, gates, Compose, smoke test, deploy e rollback.
- [x] `make verify` permanece como gate único.

## Invariantes e limites

- Migrações precisam ser compatíveis com a versão anterior; rollback destrutivo de banco não é automático.
- PostgreSQL continua sendo a fonte de verdade; Redis persiste fila, não dados de domínio.
- O gateway externo deve fornecer TLS e identidade autenticada. O pipeline não resolve a ausência atual de IdP e isolamento multi-tenant.
- Secrets de ambiente e dados reais não entram em imagem, log, atestação ou repositório.
- A implantação não remove volumes nem executa limpeza destrutiva.

## Verificação

```bash
make verify
POSTGRES_PASSWORD=test PUBLIC_ORIGIN=https://example.test \
BACKEND_IMAGE=ghcr.io/example/backend@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
FRONTEND_IMAGE=ghcr.io/example/web@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb \
docker compose -f compose.production.yaml config --quiet
```
