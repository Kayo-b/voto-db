import React, { useState } from 'react';
import DeputadoSearch from './components/DeputadoSearch';
import DeputadoDetails from './components/DeputadoDetails';
import ProposicoesRelevantes from './components/ProposicoesRelevantes';
import AnaliseAvancada from './components/AnaliseAvancada';
import VotacoesRecentes from './components/VotacoesRecentes';
import { Deputado } from './types/api';
import './App.css';

type ViewType = 'search' | 'proposicoes' | 'analise' | 'votacoes' | 'details';

function App(): React.ReactElement {
  const [currentView, setCurrentView] = useState<ViewType>('search');
  const [selectedDeputado, setSelectedDeputado] = useState<Deputado | null>(null);

  const handleSelectDeputado = (deputado: Deputado): void => {
    setSelectedDeputado(deputado);
    setCurrentView('details');
  };

  const handleBack = (): void => {
    setSelectedDeputado(null);
    setCurrentView('search');
  };

  const handleNavigation = (view: ViewType): void => {
    setCurrentView(view);
    setSelectedDeputado(null);
  };

  const renderContent = (): React.ReactElement => {
    switch (currentView) {
      case 'proposicoes':
        return <ProposicoesRelevantes />;
      case 'analise':
        return <AnaliseAvancada deputadoId={selectedDeputado?.id} />;
      case 'votacoes':
        return <VotacoesRecentes />;
      case 'details':
        return selectedDeputado ? (
          <DeputadoDetails 
            deputado={selectedDeputado} 
            onBack={handleBack} 
          />
        ) : (
          <DeputadoSearch onSelectDeputado={handleSelectDeputado} />
        );
      case 'search':
      default:
        return <DeputadoSearch onSelectDeputado={handleSelectDeputado} />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-blue-600 text-white py-6">
        <div className="container mx-auto px-4">
          <h1 className="text-3xl font-bold">VotoDB - Sistema de Análise de Votações</h1>
          <p className="text-blue-100 mt-2">
            Análise completa de deputados e votações na Câmara dos Deputados
          </p>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="container mx-auto px-4">
          <div className="flex space-x-8">
            <button
              onClick={() => handleNavigation('search')}
              className={`py-4 px-2 border-b-2 font-medium text-sm ${
                currentView === 'search' || currentView === 'details'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Buscar Deputados
            </button>
            <button
              onClick={() => handleNavigation('proposicoes')}
              className={`py-4 px-2 border-b-2 font-medium text-sm ${
                currentView === 'proposicoes'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Proposições Relevantes
            </button>
            <button
              onClick={() => handleNavigation('analise')}
              className={`py-4 px-2 border-b-2 font-medium text-sm ${
                currentView === 'analise'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Análise Avançada
            </button>
            <button
              onClick={() => handleNavigation('votacoes')}
              className={`py-4 px-2 border-b-2 font-medium text-sm ${
                currentView === 'votacoes'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Votações Recentes
            </button>
          </div>
        </div>
      </nav>

      <main className="container mx-auto px-4 py-8">
        {renderContent()}
      </main>

      <footer className="bg-gray-800 text-white py-4 mt-12">
        <div className="container mx-auto px-4 text-center">
          <p>© 2025 VotoDB - Sistema de Análise de Votações | Dados da API da Câmara dos Deputados</p>
          <p className="text-sm text-gray-300 mt-1">
            Versão 2.0 - Análise de votações em proposições de alta relevância
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
