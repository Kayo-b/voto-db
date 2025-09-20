# Notas sobre funcionamento das api usadas para a captacao de dados

## Localizando votos 

Chegando aos dados sobre votos de parlamentres em uma proposicao(PL,PEC etc)


### Caminho: Proposicao -> Parlamentar

0. Numero da proposicao deve ser manualmente localizado
   > https://www.camara.leg.br/internet/votacao/mostraVotacao.asp?ideVotacao=7492

1. id da proposicao
    > Buscando pelo numero e ano em https://www.camara.leg.br/busca-portal/proposicoes/pesquisa-simplificada

    > Por hora, nao ha nenhuma opcao de localizar programaticamente o id da proposicao.

2. id da votacao - atraves do id da proposicao
    > /api/v2/proposicoes/{idProposicao}/votacoes 

3. Lista de quem e como votou
    >  /api/v2/votacoes/{idVotacao}/votos 
