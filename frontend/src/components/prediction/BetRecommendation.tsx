import type { BetRecommendation as BetRecommendationType } from '../../types';

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
