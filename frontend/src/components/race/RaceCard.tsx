import { Link } from 'react-router-dom';
import type { Race } from '../../types';
import { GradeBadge, CourseTypeBadge } from '../common';

interface RaceCardProps {
  race: Race;
}

export function RaceCard({ race }: RaceCardProps) {
  const formattedDate = new Date(race.date).toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <Link to={`/races/${race.id}`} className="block">
      <div className="card hover:shadow-lg transition-shadow duration-200">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <GradeBadge grade={race.grade} />
              <CourseTypeBadge type={race.course_type} />
            </div>
            <h3 className="text-lg font-semibold text-gray-900">{race.name}</h3>
            <p className="text-sm text-gray-500 mt-1">
              {formattedDate} / {race.venue} / {race.distance}m
            </p>
          </div>
          <div className="text-right">
            {race.entries_count !== null && (
              <span className="text-sm text-gray-500">
                {race.entries_count}頭
              </span>
            )}
            {race.track_condition && (
              <p className="text-xs text-gray-400 mt-1">
                馬場: {race.track_condition}
              </p>
            )}
          </div>
        </div>
      </div>
    </Link>
  );
}
