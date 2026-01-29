import React, { useState } from 'react';
import { api } from '../services/api';
import { Deputado } from '../types/api';

interface DeputadoSearchProps {
  onSelectDeputado: (deputado: Deputado) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  searchResults: Deputado[];
  setSearchResults: (results: Deputado[]) => void;
}

const DeputadoSearch: React.FC<DeputadoSearchProps> = ({
  onSelectDeputado,
  searchQuery,
  setSearchQuery,
  searchResults,
  setSearchResults,
}) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const handleSearch = async (): Promise<void> => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    setError('');
    try {
      const response = await api.searchDeputados(searchQuery);
      setSearchResults(response.dados || []);
    } catch (error) {
      console.error('Erro na busca:', error);
      setError('Erro ao buscar deputados. Tente novamente.');
    }
    setLoading(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="max-w-4xl">
      {/* Search Card */}
      <div className="card p-6 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
              <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              placeholder="Digite o nome do deputado..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              className="input pl-12"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading || !searchQuery.trim()}
            className="btn-primary px-6"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Buscando...
              </>
            ) : (
              'Buscar'
            )}
          </button>
        </div>
        <p className="text-sm text-slate-500 mt-3">
          Pesquise por nome para encontrar deputados federais e analisar seus votos
        </p>
      </div>

      {/* Error State */}
      {error && (
        <div className="mb-6 p-4 rounded-lg bg-red-50 border border-red-200 flex items-start gap-3">
          <svg className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <p className="font-medium text-red-800">Erro na busca</p>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        </div>
      )}

      {/* Results */}
      {searchResults.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm font-medium text-slate-700">
            {searchResults.length} deputado{searchResults.length !== 1 ? 's' : ''} encontrado{searchResults.length !== 1 ? 's' : ''}
          </p>
          <div className="grid gap-3">
            {searchResults.map((dep) => (
              <button
                key={dep.id}
                onClick={() => onSelectDeputado(dep)}
                className="card-hover p-4 text-left w-full group"
              >
                <div className="flex items-center gap-4">
                  {dep.urlFoto ? (
                    <img
                      src={dep.urlFoto}
                      alt={dep.nome}
                      className="w-14 h-14 rounded-full object-cover ring-2 ring-slate-100"
                    />
                  ) : (
                    <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center">
                      <svg className="w-7 h-7 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                      {dep.nome}
                    </h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                        {dep.siglaPartido}
                      </span>
                      <span className="text-sm text-slate-500">{dep.siglaUf}</span>
                    </div>
                    {dep.email && (
                      <p className="text-sm text-slate-500 truncate mt-1">{dep.email}</p>
                    )}
                  </div>
                  <svg className="w-5 h-5 text-slate-400 group-hover:text-blue-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {searchResults.length === 0 && !loading && searchQuery && (
        <div className="text-center py-12">
          <svg className="w-16 h-16 mx-auto text-slate-300 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-slate-600 font-medium">Nenhum deputado encontrado</p>
          <p className="text-sm text-slate-500 mt-1">Tente buscar com outro nome</p>
        </div>
      )}

      {/* Initial State */}
      {searchResults.length === 0 && !loading && !searchQuery && !error && (
        <div className="text-center py-12">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-blue-50 mb-4">
            <svg className="w-10 h-10 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          </div>
          <p className="text-slate-600 font-medium">Busque um deputado</p>
          <p className="text-sm text-slate-500 mt-1 max-w-sm mx-auto">
            Digite o nome para pesquisar e visualizar o histórico de votações em proposições relevantes
          </p>
        </div>
      )}
    </div>
  );
};

export default DeputadoSearch;
