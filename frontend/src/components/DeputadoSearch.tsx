import React, { useState } from 'react';
import { api } from '../services/api';
import { Deputado } from '../types/api';

interface DeputadoSearchProps {
  onSelectDeputado: (deputado: Deputado) => void;
}

const DeputadoSearch: React.FC<DeputadoSearchProps> = ({ onSelectDeputado }) => {
  const [search, setSearch] = useState<string>('');
  const [deputados, setDeputados] = useState<Deputado[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const handleSearch = async (): Promise<void> => {
    setLoading(true);
    setError('');
    try {
      const response = await api.searchDeputados(search);
      setDeputados(response.dados || []);
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
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Buscar Deputado</h2>
      
      <div className="flex gap-2 mb-4">
        <input
          type="text"
          placeholder="Nome do deputado..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyPress={handleKeyPress}
          className="border border-gray-300 p-2 rounded flex-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button 
          onClick={handleSearch}
          disabled={loading}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 disabled:bg-blue-300 disabled:cursor-not-allowed"
        >
          {loading ? 'Buscando...' : 'Buscar'}
        </button>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      <div className="grid gap-2">
        {deputados.map((dep) => (
          <div 
            key={dep.id}
            onClick={() => onSelectDeputado(dep)}
            className="border border-gray-200 p-3 rounded cursor-pointer hover:bg-gray-100 transition-colors"
          >
            <h3 className="font-bold text-lg">{dep.nome}</h3>
            <p className="text-gray-600">{dep.siglaPartido} - {dep.siglaUf}</p>
            {dep.email && <p className="text-sm text-gray-500">{dep.email}</p>}
          </div>
        ))}
      </div>

      {deputados.length === 0 && !loading && search && (
        <p className="text-gray-500 text-center mt-4">
          Nenhum deputado encontrado.
        </p>
      )}
    </div>
  );
};

export default DeputadoSearch;