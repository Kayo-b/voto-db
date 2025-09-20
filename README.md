# voto-db

Plataforma de coleta, armazenamento, catalogação e cruzamento de dados angariados primariamente de fontes oficiais do governo brasileiro, com o fim de facilitar o acesso ao histórico e perfil de parlamentares e partidos.

## MVP - Transparência

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

### Busca e Filtros (nice to have)
- Buscar deputado/partido por nome
- Filtrar votações por tema/período
- Filtrar por tipo de proposição (PL, PEC, etc.)

## Problemas

- API 'dados abertos' passa por timeouts frequentes, múltiplos (2-4) requests são necessários para conseguir uma resposta.
- Descobrir uma forma simples de listar os principais projetos de lei e vinculá-los aos seus respectivos IDs para possibilitar as buscas subsequentes.

## Links úteis

https://dadosabertos.camara.leg.br/swagger/api.html  
https://www2.camara.leg.br/transparencia/dados-abertos/dados-abertos-legislativo/webservices  
https://www.camara.leg.br/proposicoesWeb
