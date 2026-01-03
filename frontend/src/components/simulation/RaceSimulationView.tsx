import { useState } from 'react';
import type { RaceSimulation } from '../../types/simulation';
import { StartFormationDiagram } from './StartFormationDiagram';
import { PositionChart } from './PositionChart';
import { ScenarioComparison } from './ScenarioComparison';
import { TrackConditionComparison } from './TrackConditionComparison';
import { RaceAnimation } from './RaceAnimation';

interface RaceSimulationViewProps {
  simulation: RaceSimulation;
}

type TabType = 'formation' | 'position' | 'scenario' | 'track' | 'animation';

export function RaceSimulationView({ simulation }: RaceSimulationViewProps) {
  const [activeTab, setActiveTab] = useState<TabType>('formation');

  const tabs: { key: TabType; label: string }[] = [
    { key: 'formation', label: '隊列予想' },
    { key: 'position', label: '位置取り' },
    { key: 'scenario', label: 'ペース別' },
    { key: 'track', label: '馬場別' },
    { key: 'animation', label: 'アニメーション' },
  ];

  // 馬場状態のバッジカラー
  const getTrackConditionColor = (condition: string | null) => {
    switch (condition) {
      case '良': return 'bg-green-100 text-green-800';
      case '稍重': return 'bg-yellow-100 text-yellow-800';
      case '重': return 'bg-orange-100 text-orange-800';
      case '不良': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold">展開シミュレーション</h2>
        <div className="flex items-center gap-2">
          {simulation.venue && (
            <span className="text-sm font-medium text-gray-700">
              {simulation.venue}
            </span>
          )}
          <span className="text-sm text-gray-500">
            {simulation.distance}m {simulation.course_type}
          </span>
          {simulation.track_condition && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getTrackConditionColor(simulation.track_condition)}`}>
              {simulation.track_condition}
            </span>
          )}
        </div>
      </div>

      {/* 競馬場特性説明 */}
      {simulation.venue_description && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 text-sm text-blue-800">
          📍 {simulation.venue_description}
        </div>
      )}

      {/* Tab navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`py-2 px-1 border-b-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'formation' && (
          <StartFormationDiagram formation={simulation.start_formation} />
        )}

        {activeTab === 'position' && (
          <PositionChart cornerPositions={simulation.corner_positions} />
        )}

        {activeTab === 'scenario' && (
          <ScenarioComparison
            scenarios={simulation.scenarios}
            currentPace={simulation.predicted_pace}
          />
        )}

        {activeTab === 'track' && (
          <TrackConditionComparison
            scenarios={simulation.track_condition_scenarios}
            currentCondition={simulation.track_condition}
          />
        )}

        {activeTab === 'animation' && simulation.animation_frames && (
          <RaceAnimation
            frames={simulation.animation_frames}
            distance={simulation.distance}
            courseType={simulation.course_type}
          />
        )}

        {activeTab === 'animation' && !simulation.animation_frames && (
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="text-lg font-semibold mb-4">レースアニメーション</h3>
            <p className="text-gray-500">アニメーションデータがありません</p>
          </div>
        )}
      </div>
    </div>
  );
}
