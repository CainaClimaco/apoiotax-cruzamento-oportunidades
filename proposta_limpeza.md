# Proposta de Limpeza de Código

> Nenhuma alteracao deve ser executada sem revisão. Este documento e apenas uma proposta.
> Ordenado por prioridade: critico -> alto -> medio -> baixo.

---

## CRITICO: Bugs que quebram funcionalidades em producao

### 1. Caminhos de template quebrados em `write_excel.py`

**O que e:** Os metodos `excel_escrituracao` (linha 24) e `excel_receita` (linhas 74, 93,
109, 125, 141, 157, 166) constroem caminhos para templates Excel usando
`os.path.join(root_directory, 'assets\\templates\\...')`, onde `root_directory` aponta
para `src/`. Os templates foram movidos para `src/cruzamento/assets/templates/` mas o
codigo nao foi atualizado.

**Por que pode ser corrigido:** Os templates existem no novo local. O codigo em
`excel_uso_consumo` e `excel_fase1` ja usa o caminho correto. E uma inconsistencia de
migracao.

**Risco de alteracao:** Baixo - e apenas correcao de caminho. Mas deve ser testado nos
modos ESCRITURACAO e RECEITA apos a mudanca.

**Recomendacao:** Corrigir. Substituir todas as ocorrencias de
`os.path.join(root_directory, 'assets\\templates\\...')` por
`os.path.join(directory, 'assets', 'templates', '...')` onde `directory` e o diretorio
do proprio `write_excel.py` (que ja aponta para `src/cruzamento/`).

---

### 2. `import os` ausente em `uso_consumo.py`

**O que e:** A linha 222 de `uso_consumo.py` chama `os.environ.get("GEMINI_API_KEY", "")`
mas o modulo `os` nao esta na lista de imports.

**Por que pode ser corrigido:** E uma importacao esquecida. O codigo funciona enquanto
a chave estiver no JSON de config (`gemini_api_key`), mas falha com `NameError` se a
chave vier apenas da variavel de ambiente.

**Risco de alteracao:** Zero. Adicionar `import os` ao cabecalho nao quebra nada.

**Recomendacao:** Corrigir imediatamente. Adicionar `import os` em `uso_consumo.py`.

---

## ALTO: Problemas que afetam confiabilidade ou manutenibilidade imediata

### 3. `requirements.txt` incompleto

**O que e:** O arquivo lista apenas `openai>=1.0` e a dependencia privada VerseTricks.
Faltam `polars`, `openpyxl`, e opcionalmente `google-generativeai` (usada pelo
classificador Gemini).

**Por que pode ser corrigido:** Sao dependencias reais, instaladas manualmente mas nao
declaradas. Um novo colaborador que criar o `venv` seguindo o `requirements.txt` nao
conseguira executar o projeto.

**Risco de alteracao:** Zero. Adicionar dependencias ao `requirements.txt` nao afeta
codigo em execucao.

**Recomendacao:** Corrigir. Adicionar ao `requirements.txt`:
```
polars
openpyxl
google-generativeai
```

---

### 4. Modulos de bloco criados mas nao conectados

**O que sao:** `dados_bloco_a.py`, `dados_bloco_e.py`, `dados_bloco_f.py` e
`dados_bloco_m.py` contem extratores bem escritos e documentados, mas nenhum deles e
importado pelo fluxo da FASE1 ou qualquer outro modulo.

**Por que pode ser mantido por enquanto:** Foram criados intencionalmente como
infraestrutura para expansao do FASE1. Removê-los eliminaria trabalho ja feito. A
recomendacao e manter e conectar, nao remover.

**Risco de remocao:** Baixo se removidos (nao quebram nada pois nao sao usados). Mas
seria desperdicio de trabalho ja feito.

**Recomendacao:** Manter e conectar ao `cruzamento_fase1.py` como proxima tarefa de
desenvolvimento. Prioridade: Bloco D (CT-e) ja esta conectado e pode servir de modelo
para os demais.

---

## MEDIO: Duplicacoes e acoplamentos que criam risco de divergencia futura

### 5. `_get_versao` duplicada

**O que e:** Funcao identica definida em `uso_consumo.py:39` e `fase1.py:19`.

**Por que pode ser removida:** Com o crescimento do projeto, se a logica precisar mudar
(ex: mudanca no campo `VERSAO` do SPED), sera necessario lembrar de atualizar em dois
lugares.

**Risco de alteracao:** Baixo. Extrair para `dados_uso_consumo.py` ou um modulo
`utils.py` e importar nos dois lugares.

**Recomendacao:** Refatorar. Mover para `dados_uso_consumo.py` que ja contem utilitarios
compartilhados, e importar de la.

---

### 6. `_build_item_key` duplicada com variacoes

**O que e:** Logica de construcao de chave de cruzamento definida em `uso_consumo.py`
(linhas 49-133, com dois metodos: `_build_join_key` e `_build_item_key`) e em
`cruzamento_fase1.py:207` (versao simplificada). Sao parecidas mas diferentes o
suficiente para divergir com futuras mudancas.

**Risco de alteracao:** Medio. Unificar requer entender as diferencas sutis de contexto
(uso_consumo usa nivel de item com NUM_ITEM; cruzamento_fase1 consolida por PERIODO +
COD_ITEM antes de construir a chave).

**Recomendacao:** Refatorar quando o FASE1 estiver estabilizado. Nao e urgente mas e
divida tecnica crescente.

---

### 7. Acoplamento implicito em `dados_receita.py`

**O que e:** As funcoes `process_contribuicoes` (linha 157) e `process_fiscal` (linha 258)
recebem `df_json` como parametro mas internamente filtram pelo registro hardcoded
(`cd.reg_receita_C` e `cd.reg_receita_F`). Isso cria a ilusao de que as funcoes sao
genericas quando na verdade sao especificas do modo RECEITA.

**Risco de alteracao:** Medio. Nao causa bug hoje (so sao chamadas pelo modo RECEITA),
mas pode causar confusao se alguem tentar reusar para FASE1 ou outro modo.

**Recomendacao:** Renomear para `process_contribuicoes_receita` e `process_fiscal_receita`
para tornar explicito o acoplamento, ou aceitar o parametro de registro como argumento.

---

## BAIXO: Limpeza cosmetica e de desenvolvimento

### 8. Codigo comentado em `file_reader.py`

**O que e:** Implementacoes antigas de `renomear_colunas` (linhas 19-23 e 38-39) mantidas
como comentario.

**Por que pode ser removido:** A implementacao atual (linhas 26-33) substituiu as
anteriores. O historico git preserva as versoes antigas se necessario.

**Risco de remocao:** Zero.

**Recomendacao:** Remover.

---

### 9. `src/create_template_uc.py`

**O que e:** Script one-shot que gera o `Template_Uso_Consumo.xlsx`. O template ja existe
em `src/cruzamento/assets/templates/`. O script nao e chamado pelo fluxo normal.

**Por que pode ser mantido:** Permite regenerar o template se ele for corrompido ou
atualizado visualmente. E util como documentacao viva do layout.

**Risco de remocao:** Baixo - o template existente em `assets/templates/` continuaria
funcionando mesmo sem o script.

**Recomendacao:** Manter, mas mover para uma pasta `scripts/` ou `tools/` para deixar
claro que nao faz parte do fluxo de producao.

---

### 10. Artefatos de desenvolvimento na raiz

**O que sao:**
- `teste_fase1.py`: script standalone nao comitado, util para testes locais do FASE1.
- `test_fase1_output.xlsx`: output gerado pelo script acima.

**Recomendacao:** Mover `teste_fase1.py` para `tests/` (ou `scripts/`). Adicionar
`*.xlsx` (ou especificamente `test_*.xlsx`) ao `.gitignore` para nao commitar outputs.

---

### 11. Chaves duplicadas na configuracao JSON

**O que e:** `uso_consumo_config.json` contem `cst_com_credito` e `cst_sem_credito`,
que sao listas de CSTs para fallback. Porem `classificador_llm.py` usa seus proprios
conjuntos hardcoded (`_CST_ELEGIVEL`, `_CST_NAO_ELEGIVEL`) e nao le essas chaves do JSON.

**Risco de divergencia:** Se alguem atualizar o JSON esperando que o comportamento mude,
nada acontecera. Os conjuntos do `classificador_llm.py` continuam valendo.

**Recomendacao:** Remover as chaves do JSON (ou fazer o `classificador_llm.py` le-las).
Preferencia: ler do JSON para manter a configurabilidade.

---

## Resumo por prioridade

| # | Item | Prioridade | Acao |
|---|---|---|---|
| 1 | Caminhos de template em `write_excel.py` | CRITICO | Corrigir |
| 2 | `import os` em `uso_consumo.py` | CRITICO | Corrigir |
| 3 | `requirements.txt` incompleto | ALTO | Corrigir |
| 4 | Blocos A/E/F/M sem conexao | ALTO | Manter e conectar |
| 5 | `_get_versao` duplicada | MEDIO | Refatorar |
| 6 | `_build_item_key` duplicada | MEDIO | Refatorar (pos-FASE1 estavel) |
| 7 | Acoplamento em `dados_receita.py` | MEDIO | Renomear |
| 8 | Codigo comentado em `file_reader.py` | BAIXO | Remover |
| 9 | `create_template_uc.py` na raiz | BAIXO | Mover para scripts/ |
| 10 | Artefatos de teste na raiz | BAIXO | Mover/gitignore |
| 11 | CSTs duplicados JSON vs codigo | BAIXO | Unificar |
