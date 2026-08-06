# Guia de Contribuição

Este documento descreve as diretrizes para contribuir com este projeto.

## Processo de Desenvolvimento

1. Crie uma nova branch a partir da `main` para suas alterações
2. Faça suas alterações seguindo as convenções de código
3. Envie um Pull Request para a branch `main`
4. Aguarde a revisão e aprovação

## Convenções de Commits

Utilize prefixos nos commits para facilitar o entendimento:

- `FEAT`: Nova funcionalidade
- `FIX`: Correção de bug
- `DOCS`: Alterações na documentação
- `REFACTOR`: Refatoração de código sem alteração de comportamento
- `TEST`: Adição ou modificação de testes
- `CHORE`: Alterações em processos de build, ferramentas, etc.
- `BREAKING`: Alterações que quebram compatibilidade

Exemplo:
```
FEAT: Adiciona autenticação por JWT
```

## Padrões de Código

- Siga os padrões de estilo definidos nos arquivos de configuração
- Documente novas funções e classes
- Escreva testes para novas funcionalidades
- Mantenha a cobertura de testes

## Pull Requests

- Descreva claramente o que foi alterado
- Referencie issues relacionadas
- Aguarde a revisão de pelo menos um mantenedor 
- Utilize o template dentro de `./github/pull_request_template.md`sempre que possível