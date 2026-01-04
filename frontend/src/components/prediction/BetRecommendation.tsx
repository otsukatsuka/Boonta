import type { BetRecommendation as BetRecommendationType } from '../../types';

interface BetRecommendationProps {
  bets: BetRecommendationType;
}

export function BetRecommendation({ bets }: BetRecommendationProps) {
  // 新形式か旧形式かを判定
  const isNewFormat = bets.trifecta_multi !== undefined || (bets.trio && 'pivots' in bets.trio);

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">推奨買い目</h3>

      {bets.note && (
        <p className="text-sm text-gray-600 mb-4 bg-yellow-50 p-2 rounded border border-yellow-200">
          {bets.note}
        </p>
      )}

      <div className="space-y-4">
        {isNewFormat ? (
          // 新形式: 三連複（軸2頭流し）+ 三連単2頭軸マルチ
          <>
            {bets.trio && 'pivots' in bets.trio && (
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <span className="font-semibold text-gray-900 text-lg">三連複</span>
                    <span className="ml-2 text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                      軸2頭流し
                    </span>
                  </div>
                  <div className="text-right text-sm">
                    <div className="text-gray-500">
                      {bets.trio.combinations}点 × ¥{bets.trio.amount_per_ticket.toLocaleString()}
                    </div>
                    <div className="font-bold text-lg">
                      ¥{(bets.trio.combinations * bets.trio.amount_per_ticket).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 rounded p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-red-600 w-12">軸:</span>
                    <div className="flex gap-1">
                      {(bets.trio as any).pivots.map((num: number) => (
                        <span key={num} className="inline-flex items-center justify-center w-8 h-8 bg-red-600 text-white font-bold rounded">
                          {num}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-600 w-12">相手:</span>
                    <div className="flex gap-1">
                      {(bets.trio as any).others.map((num: number) => (
                        <span key={num} className="inline-flex items-center justify-center w-8 h-8 bg-gray-700 text-white font-bold rounded">
                          {num}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {bets.trifecta_multi && (
              <div className="border-2 border-red-200 rounded-lg p-4 bg-red-50">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <span className="font-semibold text-red-800 text-lg">三連単</span>
                    <span className="ml-2 text-xs text-red-600 bg-red-100 px-2 py-0.5 rounded font-medium">
                      2頭軸マルチ
                    </span>
                  </div>
                  <div className="text-right text-sm">
                    <div className="text-gray-500">
                      {bets.trifecta_multi.combinations}点 × ¥{bets.trifecta_multi.amount_per_ticket.toLocaleString()}
                    </div>
                    <div className="font-bold text-lg text-red-700">
                      ¥{(bets.trifecta_multi.combinations * bets.trifecta_multi.amount_per_ticket).toLocaleString()}
                    </div>
                  </div>
                </div>
                <div className="bg-white rounded p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-red-600 w-12">軸:</span>
                    <div className="flex gap-1">
                      {bets.trifecta_multi.pivots.map((num) => (
                        <span key={num} className="inline-flex items-center justify-center w-8 h-8 bg-red-600 text-white font-bold rounded">
                          {num}
                        </span>
                      ))}
                    </div>
                    <span className="text-xs text-gray-500 ml-2">(順不同)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-600 w-12">相手:</span>
                    <div className="flex gap-1">
                      {bets.trifecta_multi.others.map((num) => (
                        <span key={num} className="inline-flex items-center justify-center w-8 h-8 bg-gray-700 text-white font-bold rounded">
                          {num}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
                <p className="text-xs text-red-600 mt-2">
                  マルチ: 軸2頭が1-2-3着のいずれかに入れば的中
                </p>
              </div>
            )}
          </>
        ) : (
          // 旧形式: trifecta, trio, exacta, wide
          <>
            {(bets as any).trifecta && (
              <BetSection
                title="三連単"
                type={(bets as any).trifecta.type}
                content={
                  <div className="text-sm">
                    <div>1着: {(bets as any).trifecta.first.join(', ')}</div>
                    <div>2着: {(bets as any).trifecta.second.join(', ')}</div>
                    <div>3着: {(bets as any).trifecta.third.join(', ')}</div>
                  </div>
                }
                combinations={(bets as any).trifecta.combinations}
                amount={(bets as any).trifecta.amount_per_ticket}
              />
            )}

            {bets.trio && 'horses' in bets.trio && (
              <BetSection
                title="三連複"
                type={(bets.trio as any).type}
                content={
                  <div className="text-sm">
                    BOX: {(bets.trio as any).horses.join(' - ')}
                  </div>
                }
                combinations={bets.trio.combinations}
                amount={bets.trio.amount_per_ticket}
              />
            )}

            {(bets as any).exacta && (
              <BetSection
                title="馬単"
                type={(bets as any).exacta.type}
                content={
                  <div className="text-sm">
                    {(bets as any).exacta.first} → {(bets as any).exacta.second.join(', ')}
                  </div>
                }
                combinations={(bets as any).exacta.combinations}
                amount={(bets as any).exacta.amount_per_ticket}
              />
            )}

            {(bets as any).wide && (
              <BetSection
                title="ワイド"
                type="穴狙い"
                content={
                  <div className="text-sm">
                    {(bets as any).wide.pairs.map((pair: number[], i: number) => (
                      <div key={i}>{pair.join(' - ')}</div>
                    ))}
                    {(bets as any).wide.note && (
                      <div className="text-yellow-600 text-xs mt-1">
                        {(bets as any).wide.note}
                      </div>
                    )}
                  </div>
                }
                combinations={(bets as any).wide.pairs.length}
                amount={(bets as any).wide.amount_per_ticket}
              />
            )}
          </>
        )}
      </div>

      {/* 合計投資額 */}
      <div className="mt-6 pt-4 border-t-2 border-gray-300">
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
