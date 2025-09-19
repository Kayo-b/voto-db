# voto-db

Plataforma de coleta, armazenamento, catalogação e cruzamento de dados angariados primariamente de fontes oficiais do governo brasileiro, com fim de facilitar o acesso ao histórico e perfil de parlamentares e partidos.


## mvp - transparencia

### Perfil Individual do Deputado
- Nome, partido, estado
- Histórico de votações (Sim/Não/Abstenção/Ausente)
- Percentual de alinhamento com o partido
- Leis mais importantes que votou

### Análise de Votações por Lei/PEC
- Título e descrição da proposição
- Resultado final (Aprovado/Rejeitado)
- Como cada deputado votou
- Breakdown por partido (% que votou Sim/Não)

### Perfil do Partido
- Posicionamento majoritário em votações-chave
- Disciplina partidária (% de votos alinhados)
- Comparação com outros partidos
- Leis que o partido apoiou vs rejeitou


## Nice to have

### Busca e Filtros
- Buscar deputado/partido por nome
- Filtrar votações por tema/período
- Filtrar por tipo de proposição (PL, PEC, etc.)

### API Básica
- Endpoint para votações de um deputado
- Endpoint para resultado de uma votação específica
- Dados em JSON


#### Links uteis

https://dadosabertos.camara.leg.br/swagger/api.html
https://www2.camara.leg.br/transparencia/dados-abertos/dados-abertos-legislativo/webservices
https://www.camara.leg.br/proposicoesWeb