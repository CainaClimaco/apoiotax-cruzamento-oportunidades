# 📄 Cruzamento SPED - Escrituração e Receita
Este projeto realiza o cruzamentos de arquivos SPED (Fiscal e Contribuições) com arquivo XML de Nota Fiscal

## 🛠️ Pré-requisito
Python: Versão 3.12
Git: Para clonar o repositório.
## 🚀  Instalação e Configuração
1. Clone  este repositório
```bash
    git clone https://github.com/taxverseapp/cruzamentos_sped_nfe.git
```
2. Crie o ambiente virtual e configure as dependências necessárias(requirements.txt)
```bash
    python -m venv venv
    pip install -r requirements.txt
```
3. Caso esteja em ambiente de desenvolvimento, crie um arquivo .env com as variáveis de ambiente na pasta "envs"(exemplo: azure.env).

## 📥 Inputs necessários:
- Sped Contribuições
- Sped Fiscal ICMS/IPI
- XML padrão NF-e
>**Nota:** Não é obrigatório fornecer todos os tipos de arquivo. A análise será feita com base nos arquivos que você disponibilizar.

## ▶️ Como executar
A ferramenta é executada através da linha de comando. A estrutura básica do comando é:

```bash
    python /main.py -i <input> -n <name> -s <special>
```
#### Argumentos
| Argumento     | Descrição                          |Exemplo         |
|---------------|------------------------------------|----------------|
| -i, --input   |**Obrigatório.** O caminho para a pasta onde estão os arquivos de entrada (SPEDs e XMLs).|-i "./caminho/da/pasta"|
| -n, --name    |**Obrigatório.** Um nome para a solicitação ou projeto.|-n "Nome do Projeto"|
|-s, --special  |**Obrigatório.** Um dicionário em formato de string contendo os parâmetros da análise.|Ver detalhes abaixo.|


#### Parâmetros *special*
| Parâmetro     | Tipo   | Obrigatório | Descrição                          |Valores aceitos         |
|---------------|--------|-------------|------------------------------------|---------|
| Tipo          | string | Sim         | Cruzamento que será processado     |`EFD_F_X_EFD_C_X_NF-E_(ESCRITURACAO)` / `EFD_F_X_EFD_C_X_NF-E_(RECEITA)`|
| Solicitação   | string | Sim         | Nome do projeto a ser processado   |         |

***Exemplo completo de execução:*** 
```bash
    python main.py -i "./caminho" -n "teste" -s "{'Solicitação':'teste', 'Tipo':'EFD_F_X_EFD_C_X_NF-E_(ESCRITURACAO)'}"
```

## 📤 Resposta
### Cruzamento - Receita
O resultado, a depender dos aquivos de input enviados, poderá ser dividido entre 7 arquivos: 
1. Cruzamento, que contém a visão analítica, consolidada, trimestral e anual 
2. Relatório de SPED Fiscal
3. Relatório de SPED Contribuições
4. Relatório de dados processados
5. Relatório de NF-e
6. Relatório de dados não considerados
7. Relatório de arquivos não processados

### Cruzamento - Escrituração
O resultado será um arquivo excel contendo duas planilhas, uma com o cruzamento dos arquivos e a segunda com a relação de arquivos a serem analisados.
