# ADR 0005: Entrega por imagens imutáveis

Status: Accepted

## Contexto

O repositório possuía dois workflows de CI sobrepostos e nenhum contrato de publicação, promoção ou rollback. Reconstruir o código no servidor faria produção divergir do artefato verificado e tags mutáveis não identificariam com precisão a versão implantada.

## Decisão

Usar um único workflow de GitHub Actions. `make verify` e a integração Docker precedem qualquer efeito externo. O workflow constrói uma imagem do backend e uma do frontend uma única vez, publica no GHCR com metadados de cadeia de suprimentos e transmite ao deploy referências `imagem@sha256:digest`.

Staging acompanha a branch padrão. Produção acompanha tags `v*` e é protegida pelo environment do GitHub. O servidor usa Docker Compose, mantém segredos fora do Git, preserva a referência anterior e executa rollback de imagem quando atualização ou smoke test falha.

## Consequências

- O artefato testado é identificável e promovido sem reconstrução no servidor.
- O GitHub e o host SSH tornam-se dependências operacionais explícitas.
- Actions precisam permanecer pinadas e seus SHAs devem ser revisados nas atualizações do Dependabot.
- Migrações precisam ser retrocompatíveis porque rollback automático de schema seria inseguro.
- A solução pressupõe gateway TLS autenticado; ela não substitui o trabalho futuro de identidade e multi-tenancy.
