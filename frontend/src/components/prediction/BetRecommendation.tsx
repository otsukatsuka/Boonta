import type { BetRecommendation as BetRecommendationType, HighRiskBet } from '../../types';
import { RISK_LABELS, RISK_COLORS } from '../../types';

interface BetRecommendationProps {
  bets: BetRecommendationType;
}

export function BetRecommendation({ bets }: BetRecommendationProps) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">推奨買い目</h3>

      {bets.note && (
        <p className="text-sm text-gray-600 mb-4 bg-gray-50 p-2 rounded">
          {bets.note}
        </p>
      )}

      <div className="space-y-4">
        {bets.trifecta && (
          <BetSection
            title="三連単"
            type={bets.trifecta.type}
            content={
              <div className="text-sm">
                <div>1着: {bets.trifecta.first.join(', ')}</div>
                <div>2着: {bets.trifecta.second.join(', ')}</div>
                <div>3着: {bets.trifecta.third.join(', ')}</div>
              </div>
            }
            combinations={bets.trifecta.combinations}
            amount={bets.trifecta.amount_per_ticket}
          />
        )}

        {bets.trio && (
          <BetSection
            title="三連複"
            type={bets.trio.type}
            content={
              <div className="text-sm">
                BOX: {bets.trio.horses.join(' - ')}
              </div>
            }
            combinations={bets.trio.combinations}
            amount={bets.trio.amount_per_ticket}
          />
        )}

        {bets.exacta && (
          <BetSection
            title="馬単"
            type={bets.exacta.type}
            content={
              <div className="text-sm">
                {bets.exacta.first} → {bets.exacta.second.join(', ')}
              </div>
            }
            combinations={bets.exacta.combinations}
            amount={bets.exacta.amount_per_ticket}
          />
        )}

        {bets.wide && (
          <BetSection
            title="ワイド"
            type="穴狙い"
            content={
              <div className="text-sm">
                {bets.wide.pairs.map((pair, i) => (
                  <div key={i}>{pair.join(' - ')}</div>
                ))}
                {bets.wide.note && (
                  <div className="text-yellow-600 text-xs mt-1">
                    {bets.wide.note}
                  </div>
                )}
              </div>
            }
            combinations={bets.wide.pairs.length}
            amount={bets.wide.amount_per_ticket}
          />
        )}
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200">
        <div className="flex justify-between items-center">
          <span className="text-lg font-semibold">合計投資額</span>
          <span className="text-2xl font-bold text-primary-600">
            ¥{bets.total_investment.toLocaleString()}
          </span>
        </div>
      </div>

      {/* High Risk Bets Section */}
      {bets.high_risk_bets && bets.high_risk_bets.length > 0 && (
        <HighRiskBetsSection bets={bets.high_risk_bets} />
      )}
    </div>
  );
}

interface HighRiskBetsSectionProps {
  bets: HighRiskBet[];
}

function HighRiskBetsSection({ bets }: HighRiskBetsSectionProps) {
  const totalHighRiskInvestment = bets.reduce((sum, b) => sum + b.amount, 0);

  return (
    <div className="mt-6 pt-4 border-t-2 border-red-200">
      <div className="flex items-center gap-2 mb-4">
        <h4 className="text-lg font-semibold text-red-700">ハイリスク・ハイリターン</h4>
        <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">穴馬中心</span>
      </div>

      <p className="text-xs text-gray-500 mb-4">
        展開と適性を考慮した穴馬中心の高配当狙い。期待リターン順に表示。
      </p>

      <div className="space-y-3">
        {bets.map((bet, index) => (
          <HighRiskBetCard key={index} bet={bet} rank={index + 1} />
        ))}
      </div>

      <div className="mt-4 p-3 bg-red-50 rounded-lg">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium text-red-700">ハイリスク投資額</span>
          <span className="text-lg font-bold text-red-700">
            ¥{totalHighRiskInvestment.toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  );
}

interface HighRiskBetCardProps {
  bet: HighRiskBet;
  rank: number;
}

function HighRiskBetCard({ bet, rank }: HighRiskBetCardProps) {
  return (
    <div className="border border-red-200 rounded-lg p-3 bg-white hover:bg-red-50 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-2">
          <span className="w-6 h-6 flex items-center justify-center bg-red-600 text-white text-xs font-bold rounded-full">
            {rank}
          </span>
          <span className="font-semibold text-gray-900">{bet.bet_type}</span>
          <span className={`text-xs px-2 py-0.5 rounded ${RISK_COLORS[bet.risk_level]}`}>
            {RISK_LABELS[bet.risk_level]}
          </span>
        </div>
        <div className="text-right">
          <div className="text-xs text-gray-500">期待リターン</div>
          <div className="font-bold text-red-600">{bet.expected_return.toFixed(1)}倍</div>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm text-gray-600">馬番:</span>
        <div className="flex gap-1">
          {bet.horses.map((num) => (
            <span
              key={num}
              className="inline-flex items-center justify-center w-6 h-6 bg-gray-800 text-white text-xs font-bold rounded"
            >
              {num}
            </span>
          ))}
        </div>
        <span className="text-sm text-gray-500 ml-auto">¥{bet.amount}</span>
      </div>

      <p className="text-xs text-gray-600 bg-gray-50 p-2 rounded">{bet.reason}</p>
    </div>
  );
}

interface BetSectionProps {
  title: string;
  type: string;
  content: React.ReactNode;
  combinations: number;
  amount: number;
}

function BetSection({ title, type, content, combinations, amount }: BetSectionProps) {
  const total = combinations * amount;

  return (
    <div className="border border-gray-200 rounded-lg p-3">
      <div className="flex justify-between items-start mb-2">
        <div>
          <span className="font-medium text-gray-900">{title}</span>
          <span className="ml-2 text-xs text-gray-500">({type})</span>
        </div>
        <div className="text-right text-sm">
          <div className="text-gray-500">
            {combinations}点 × ¥{amount}
          </div>
          <div className="font-medium">¥{total.toLocaleString()}</div>
        </div>
      </div>
      <div className="bg-gray-50 rounded p-2">{content}</div>
    </div>
  );
}
