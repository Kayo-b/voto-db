import React, { useState } from 'react';
import DeputadoSearch from './components/DeputadoSearch';
import DeputadoDetails from './components/DeputadoDetails';
import { Deputado } from './types/api';
import './App.css';

function App(): React.ReactElement {
  const [selectedDeputado, setSelectedDeputado] = useState<Deputado | null>(null);

  const handleSelectDeputado = (deputado: Deputado): void => {
    setSelectedDeputado(deputado);
  };

  const handleBack = (): void => {
    setSelectedDeputado(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-blue-600 text-white py-6">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl font-bold">VotoDB - Sistema de Consulta de Deputados</h1>
          <p className="text-blue-100 mt-2">
            Consulte informações sobre deputados e suas votações na Câmara dos Deputados
          </p>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {selectedDeputado ? (
          <DeputadoDetails 
            deputado={selectedDeputado} 
            onBack={handleBack} 
          />
        ) : (
          <DeputadoSearch onSelectDeputado={handleSelectDeputado} />
        )}
      </main>

      <footer className="bg-gray-800 text-white py-4 mt-12">
        <div className="container mx-auto px-4 text-center">
          <p>© 2025 VotoDB - Dados da API da Câmara dos Deputados</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
