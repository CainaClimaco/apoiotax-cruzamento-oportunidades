# Análise de Código Não Utilizado

## 1. Módulos criados mas não conectados ao fluxo

| Arquivo | Funcoes exportadas | Importado por |
|---|---|---|
| `src/cruzamento/dados_bloco_a.py` | `extrair_a100_contribuicoes`, `extrair_a170_contribuicoes` | Nenhum |
| `src/cruzamento/dados_bloco_e.py` | `extrair_e110_fiscal`, `extrair_e210_fiscal`, `extrair_e520_fiscal` | Nenhum |
| `src/cruzamento/dados_bloco_f.py` | `extrair_f100_contribuicoes`, `extrair_f130_contribuicoes` | Nenhum |
| `src/cruzamento/dados_bloco_m.py` | `extrair_m200_contribuicoes`, `extrair_m210_contribuicoes`, `extrair_m110_contribuicoes`, `extrair_m220_contribuicoes`, `extrair_m600_contribuicoes`, `extrair_m610_contribuicoes`, `extrair_m510_contribuicoes`, `extrair_m620_contribuicoes` | Nenhum |

`dados_bloco_d.py` e a unica excecao: e importado por `cruzamento_fase1.py`.

---

## 2. Funcoes duplicadas

| Funcao | Localizacoes | Diferenca |
|---|---|---|
| `_get_versao` | `uso_consumo.py:39` e `fase1.py:19` | Identica |
| `_build_item_key` | `uso_consumo.py:93` e `cruzamento_fase1.py:207` | Logica similar, nomes de campos ligeiramente diferentes |

---

## 3. Codigo comentado

| Arquivo | Linhas | Descricao |
|---|---|---|
| `file_reader.py` | 19-23 | Implementacao antiga de `renomear_colunas` via `.rename()` simples |
| `file_reader.py` | 38-39 | Segunda implementacao alternativa via `rename_dict` |

---

## 4. Importacoes orphans / modulo ausente

| Arquivo | Problema | Linha |
|---|---|---|
| `uso_consumo.py` | `os.environ.get(...)` chamado sem `import os` | 222-225 |
| `requirements.txt` | `polars`, `openpyxl`, `google-generativeai` usados em producao mas nao listados | - |

---

## 5. Scripts de desenvolvimento nao integrados

| Arquivo | Natureza |
|---|---|
| `teste_fase1.py` (raiz) | Script standalone de teste, nao faz parte do modulo, nao comitado |
| `test_fase1_output.xlsx` (raiz) | Output gerado pelo teste acima, nao comitado |
| `src/create_template_uc.py` | Script one-shot para gerar o `Template_Uso_Consumo.xlsx`. O template ja existe em `assets/templates/`. O script nao e importado nem chamado pelo fluxo principal |
| `src/prompt_commander.log` | Arquivo de log de execucao, nao comitado |

---

## 6. Arquivos deletados mas ainda referenciados no codigo

Os templates foram movidos de `src/assets/templates/` para `src/cruzamento/assets/templates/`.
O codigo abaixo ainda referencia o caminho antigo e quebrara em runtime:

| Arquivo | Metodo | Caminho com bug |
|---|---|---|
| `write_excel.py:24` | `excel_escrituracao` | `os.path.join(root_directory, 'assets\\templates\\Template_Check SPED x XML_v5.xlsx')` |
| `write_excel.py:74` | `excel_receita` (por ano) | `os.path.join(root_directory, 'assets\\templates\\Template_ANALITICO.xlsx')` |
| `write_excel.py:93` | `excel_receita` (por ano) | `os.path.join(root_directory, 'assets\\templates\\Template_EFDFISCAL.xlsx')` |
| `write_excel.py:109` | `excel_receita` (por ano) | `os.path.join(root_directory, 'assets\\templates\\Template_EFDCONTRIBUICOES.xlsx')` |
| `write_excel.py:125` | `excel_receita` (por ano) | `os.path.join(root_directory, 'assets\\templates\\Template_NOTAS.xlsx')` |
| `write_excel.py:141` | `excel_receita` (por ano) | `os.path.join(root_directory, 'assets\\templates\\Template_XML.xlsx')` |
| `write_excel.py:157` | `excel_receita` (nao considerados) | `os.path.join(root_directory, 'assets\\templates\\Template_XML_N_CONSIDERADOS.xlsx')` |
| `write_excel.py:166` | `excel_receita` (nao processados) | `os.path.join(root_directory, 'assets\\templates\\Template_N_PROCESSADOS.xlsx')` |

`root_directory` em `write_excel.py` resolve para `src/` (pai de `src/cruzamento/`).
Os templates estao em `src/cruzamento/assets/templates/`, nao em `src/assets/templates/`.

---

## 7. Configuracoes/assets potencialmente desnecessarios

| Item | Localidade | Observacao |
|---|---|---|
| `src/envs/azure.env` | Raiz do modulo | Contem credenciais; deve estar no `.gitignore` |
| `src/cruzamento/assets/uso_consumo_config.json` chave `cst_com_credito` e `cst_sem_credito` | Config JSON | Esses valores ja estao hardcoded em `classificador_llm.py` (`_CST_ELEGIVEL`, `_CST_NAO_ELEGIVEL`). A config nao e lida por `classificador_llm.py`, que usa seus proprios conjuntos. Duplicacao silenciosa. |

---

## 8. Logica de filtro com acoplamento implicito

| Arquivo | Funcao | Problema |
|---|---|---|
| `dados_receita.py:172` | `process_contribuicoes` | Recebe `df_json` como parametro mas internamente usa `cd.reg_receita_C` fixo; o parametro `df_json` e obrigatorio mas o registro filtrado e sempre o do modo receita |
| `dados_receita.py:271` | `process_fiscal` | Mesmo padrao: usa `cd.reg_receita_F` fixo, mas o parametro `df_json` sugere flexibilidade que nao existe |
