# Resumo Executivo: Cruzamento SPED x NF-e

## Visao Geral

Ferramenta de linha de comando desenvolvida pela Apter Tecnologia para cruzamento
de obrigacoes fiscais eletronicas. Opera sobre tres inputs principais:

- **EFD ICMS/IPI** (EFD Fiscal): escrituracao de ICMS, IPI e CT-e
- **EFD Contribuicoes** (EFD_C): escrituracao de PIS/COFINS
- **XML NF-e**: notas fiscais eletronicas no padrao Modelo 55

O objetivo e identificar divergencias de escrituracao, cruzar itens de NF-e com
ambas as EFDs e gerar relatorios Excel formatados no padrao visual Apter/Taxverse.
Atende clientes da Apter (Tax/Advisory) que precisam validar compliance ou mapear
oportunidades de credito tributario.

---

## Historico Macro e Evolucao

### Fase Inicial: Escrituracao e Receita
O projeto nasceu com dois modos de operacao, ambos estaveis e em producao:

- **ESCRITURACAO**: verifica se cada NF-e esta registrada tanto no EFD Fiscal quanto no
  EFD Contribuicoes, cruzando pela chave de 44 digitos (CHV_NFE). Produz 1 arquivo
  Excel com abas "SPED x XML" e "ARQUIVOS_PARA_ANALISE".
- **RECEITA**: analise detalhada com visoes analitica, consolidada, trimestral e anual.
  Confronta valores de NF-e com os registros de cada EFD. Produz ate 7 arquivos Excel
  por ano-base (Analitico, EFD Fiscal, EFD Contribuicoes, Notas, XML, Nao Considerados,
  Nao Processados).

A decisao arquitetural central foi usar **Polars** (nao Pandas) para processamento de
dados, por performance em arquivos SPED de grande volume. O mecanismo de leitura e
parsing dos arquivos SPED e encapsulado na biblioteca interna `datatricks` (repositorio
VerseTricks), que tambem fornece o `Commander` (base class do CLI), os parsers SPED/XML
e o helper Excel (`excel_handler`).

### Fase 1: Base Completa de Cruzamento (FASE1)
Terceiro modo, ainda em desenvolvimento ativo. Extrai a base completa de itens C170 e
D190 de ambas as EFDs sem aplicar filtros de elegibilidade ou CFOP. E concebido como
pre-requisito analitico que alimenta decisoes sobre quais operacoes seguir para analise
mais profunda. A estrategia e expandir o FASE1 para cobrir uso e consumo e demais
analises de credito, substituindo qualquer abordagem anterior.

Adicionados os modulos extratores por bloco SPED (`dados_bloco_a`, `dados_bloco_d`,
`dados_bloco_e`, `dados_bloco_f`, `dados_bloco_m`) como infraestrutura de extracao
padronizada, ainda parcialmente conectada ao fluxo principal.

---

## Estado Atual

### Modos de operacao
| Modo | Modulo principal | Status |
|---|---|---|
| ESCRITURACAO | `Escrituracao.py` | Estavel, producao |
| RECEITA | `Receita.py` | Estavel, producao |
| FASE1 | `fase1.py` + `cruzamento_fase1.py` | Em desenvolvimento |

### Limpeza realizada (nesta sessao)
- Removidos: `uso_consumo.py`, `classificador_llm.py`, `create_template_uc.py`,
  `uso_consumo_config.json`, `teste_fase1.py`, `test_fase1_output.xlsx`.
- `write_excel.py`: todos os caminhos de template corrigidos de `root_directory` para
  `directory` (apontando para `src/cruzamento/assets/templates/`); funcao
  `excel_uso_consumo` removida.
- `cruzamento_definition.py`: reescrito sem constantes de USO_CONSUMO; constantes
  RAZAO_SOCIAL e DESCR_ITEM preservadas e movidas para secao FASE1.
- `dados_uso_consumo.py`: funcao `identificar_regime` removida (era a unica chamadora
  de COD_INC_TRIB, dependencia da U&C).
- `dados_bloco_f.py`: import orfao de `cruzamento_definition` removido.
- `file_reader.py`: implementacoes comentadas e docstring redundante removidos.
- `requirements.txt`: substituido `openai>=1.0` por `polars>=1.0` e `openpyxl>=3.1`.
- `main.py`: bloco `case cd.uso_consumo` removido; apenas 3 casos no match.

### Dependencias externas
| Dependencia | Natureza | Observacao |
|---|---|---|
| `datatricks` (VerseTricks) | Privada, Apter | CLI base, parsers SPED/XML, helper Excel |
| Azure (azure.env) | Servico nuvem | Armazena layouts do SPED por versao e obrigacao |

---

## Estrutura Principal

```
src/
  main.py                        Entrypoint CLI (Commander subclass)
  envs/
    azure.env                    Credenciais Azure (nao commitar)
  cruzamento/
    cruzamento_definition.py     Constantes, mapeamentos de campos, caminhos
    file_reader.py               Leitura e normalizacao de SPED/XML
    Escrituracao.py              Logica do modo ESCRITURACAO
    Receita.py                   Logica do modo RECEITA
    fase1.py                     Orquestrador do modo FASE1
    cruzamento_fase1.py          Motor de cruzamento C170/D190 da FASE1
    analise.py                   Validacoes e contagens de arquivo
    empresa.py                   Extracao de empresa/CNPJ
    write_excel.py               Geracao de todos os arquivos Excel de saida
    filtro_contr.py              Filtros especificos da EFD Contribuicoes
    transpose.py                 Fallback quando nao ha SPED disponivel
    dados_receita.py             Extracao e normalizacao para modo RECEITA
    dados_uso_consumo.py         Extracao C100/C170/0150 (compartilhado com FASE1)
    dados_bloco_a.py             Extratores Bloco A (ISS) - criado, nao conectado
    dados_bloco_d.py             Extratores Bloco D (CT-e)
    dados_bloco_e.py             Extratores Bloco E (ICMS/IPI apuracao) - criado, nao conectado
    dados_bloco_f.py             Extratores Bloco F (outras operacoes EFD_C) - criado, nao conectado
    dados_bloco_m.py             Extratores Bloco M (PIS/COFINS apuracao) - criado, nao conectado
    assets/
      CFOP.xlsx                  Tabela de CFOPs com descricao
      COD_SIT.xlsx               Situacao dos documentos fiscais
      Situacao_NF-e.xlsx         Situacoes possiveis de NF-e
      XML_CFOPs.xlsx             CFOPs aplicaveis ao cruzamento XML
      registros.json             Mapa de registros SPED por modo de operacao
      CST_PIS_COFINS.json        Descricoes dos CSTs de PIS/COFINS
      CST_ICMS.json              Descricoes dos CSTs de ICMS
      templates/
        apter_logo.png
        Template_Check SPED x XML_v5.xlsx
        Template_ANALITICO.xlsx
        Template_EFDFISCAL.xlsx
        Template_EFDCONTRIBUICOES.xlsx
        Template_NOTAS.xlsx
        Template_XML.xlsx
        Template_XML_N_CONSIDERADOS.xlsx
        Template_N_PROCESSADOS.xlsx
```

---

## Proximos Passos

### Expansao do FASE1
1. Conectar os extratores de Bloco A, E, F e M ao fluxo `executar_fase1` em
   `cruzamento_fase1.py` para ampliar a base de cruzamento alem de C170/D190.
2. Implementar a logica de Uso e Consumo sobre a base FASE1 (substituindo a
   abordagem removida).
3. Decidir se o Bloco A (ISS) deve ser cruzado com C de servicos ou tratado
   separadamente.

### Qualidade e manutencao
4. Verificar se `azure.env` esta no `.gitignore` (credenciais nao devem ser comitadas).
5. Extrair `_get_versao` (presente em `fase1.py`) para modulo utilitario se mais
   modulos precisarem dessa funcao.

### Riscos
- A dependencia do `datatricks`/VerseTricks ser privada significa que novos
  colaboradores precisam de acesso ao repositorio Apter para configurar o ambiente.
- O `azure.env` com credenciais Azure nao deve ser comitado.
