# Entrega e implantação

O ReconcileFlow usa um único workflow, `.github/workflows/ci-cd.yml`, para impedir que teste, publicação e implantação adotem critérios diferentes. A implantação é adequada a um servidor Docker interno protegido por um gateway HTTPS autenticado. Ela não transforma a limitação atual do cabeçalho confiável `X-Actor-Id` em autenticação de produção.

## Fluxo por evento

| Evento | Qualidade | Integração Docker | Publicação no GHCR | Implantação |
| --- | --- | --- | --- | --- |
| Pull request | sim | sim | não | não |
| Push em `main` | sim | sim | imagens por SHA e tag `staging` | `staging`, quando habilitado |
| Tag `v*` | sim | sim | SHA, SemVer e `latest` | `production`, quando habilitado |
| Execução manual | sim | sim | imagens por SHA | ambiente escolhido, quando habilitado |

`quality` executa o mesmo `make verify` usado localmente. `runtime-smoke` constrói o Compose local, aguarda os health checks e testa interface, API e catálogo de perfis. Somente depois desses dois gates as imagens são publicadas.

As imagens do backend e frontend recebem SBOM, proveniência e atestação no GitHub Container Registry. O deploy recebe referências por digest (`imagem@sha256:...`), nunca uma tag mutável.

## Configuração do repositório GitHub

1. Habilite GitHub Actions e permita que o workflow grave pacotes do repositório.
2. Crie os environments `staging` e `production` em **Settings > Environments**.
3. Exija revisores no environment `production`. O push da tag ficará aguardando essa aprovação.
4. Configure os mesmos nomes abaixo em cada environment, com valores próprios para cada servidor.

Depois que os dois ambientes estiverem prontos, crie no repositório a variable `DEPLOY_ENABLED` com valor `true`. Enquanto ela estiver ausente ou diferente de `true`, qualidade, integração e publicação continuam funcionando, mas nenhum servidor recebe alterações.

Secrets:

- `DEPLOY_HOST`: nome DNS ou IP do servidor;
- `DEPLOY_USER`: usuário SSH com acesso ao Docker;
- `DEPLOY_SSH_KEY`: chave privada exclusiva da automação;
- `DEPLOY_KNOWN_HOSTS`: linha validada de `known_hosts`, obtida por um canal administrativo confiável.

Variables:

- `DEPLOY_PATH`: caminho absoluto sem espaços, por exemplo `/opt/reconcileflow`;
- `DEPLOY_PORT`: porta SSH; quando omitida, usa `22`;
- `PUBLIC_URL`: URL HTTPS completa, sem barra final, por exemplo `https://reconcileflow.exemplo.com`.

Proteja a branch padrão exigindo os checks **Qualidade e testes** e **Integração Docker**, além de revisão do pull request. O `GITHUB_TOKEN` é usado apenas durante a execução para publicar e baixar pacotes. No servidor, ele fica em um diretório temporário exclusivo da execução, removido ao final, e não é gravado no repositório nem em sua configuração Docker permanente.

## Preparação de cada servidor

Pré-requisitos:

- Linux com Docker Engine e Docker Compose v2;
- usuário de deploy sem login por senha, autorizado a executar Docker;
- acesso de saída a `ghcr.io`;
- proxy reverso/gateway com TLS e autenticação real;
- rotina externa de backup e restauração do volume PostgreSQL.

Crie o diretório e o arquivo de configuração uma vez:

```bash
sudo install -d -o deploy -g deploy -m 750 /opt/reconcileflow
sudo install -o deploy -g deploy -m 600 .env.production.example /opt/reconcileflow/.env.production
sudoedit /opt/reconcileflow/.env.production
```

Use uma senha longa e exclusiva em `POSTGRES_PASSWORD` e a origem HTTPS real em `PUBLIC_ORIGIN`. O Compose publica o Nginx somente em `127.0.0.1:8080` por padrão. O gateway deve encaminhar para esse endereço, encerrar TLS, autenticar o usuário e substituir qualquer `X-Actor-Id` recebido externamente por uma identidade confiável.

O arquivo `.env.production` fica exclusivamente no servidor e nunca deve ser enviado ao Git. O pipeline envia apenas o Compose e os scripts públicos. No primeiro deploy ele cria `.env.release` com os dois digests aprovados.

## Publicação e promoção

Um merge na branch padrão promove automaticamente a mesma revisão para `staging` depois dos gates. Para produção, crie uma tag SemVer sobre um commit já verificado:

```bash
git tag -a v1.0.0 -m "ReconcileFlow 1.0.0"
git push origin v1.0.0
```

O environment `production` deve reter o job até a aprovação humana. Uma execução manual permite republicar e implantar uma revisão específica, mas não ignora testes nem a proteção do environment.

## Estratégia de implantação e rollback

No servidor, `scripts/deploy_remote.sh`:

1. rejeita imagens sem digest SHA-256;
2. preserva `.env.release` como `.env.release.previous`;
3. valida a configuração do Compose;
4. baixa as imagens, executa a migração e aguarda todos os health checks;
5. executa o smoke test local;
6. restaura a versão anterior automaticamente se qualquer etapa falhar.

O rollback de imagem não desfaz uma migração de banco. Toda migração deve, portanto, ser compatível com a versão anterior durante a janela de implantação. Para um rollback manual de imagens:

```bash
cd /opt/reconcileflow
cp -p .env.release.previous .env.release
docker compose --env-file .env.production --env-file .env.release \
  -f compose.production.yaml up -d --remove-orphans --wait --wait-timeout 180
bash scripts/smoke_test.sh http://127.0.0.1:8080
```

Teste periodicamente a restauração do PostgreSQL em ambiente isolado. Redis persiste a fila com AOF, mas não substitui o banco nem deve ser tratado como fonte de verdade.

## Diagnóstico

No servidor:

```bash
cd /opt/reconcileflow
docker compose --env-file .env.production --env-file .env.release \
  -f compose.production.yaml ps
docker compose --env-file .env.production --env-file .env.release \
  -f compose.production.yaml logs --tail=200
```

No GitHub, abra a execução de **CI/CD**. Falhas antes de `Publicar imagens` não alteram registry ou servidor; falhas na aprovação não iniciam a conexão SSH; falhas durante a implantação acionam o rollback de imagem e permanecem visíveis no job.
