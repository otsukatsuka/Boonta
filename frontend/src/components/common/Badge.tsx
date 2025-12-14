import type { Grade, RunningStyle, WorkoutEvaluation } from '../../types';
import { RUNNING_STYLE_LABELS } from '../../types';

interface GradeBadgeProps {
  grade: Grade;
}

export function GradeBadge({ grade }: GradeBadgeProps) {
  const colorClasses: Record<Grade, string> = {
    G1: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    G2: 'bg-pink-100 text-pink-800 border-pink-300',
    G3: 'bg-purple-100 text-purple-800 border-purple-300',
    OP: 'bg-blue-100 text-blue-800 border-blue-300',
    L: 'bg-gray-100 text-gray-800 border-gray-300',
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${colorClasses[grade]}`}
    >
      {grade}
    </span>
  );
}

interface RunningStyleBadgeProps {
  style: RunningStyle;
}

export function RunningStyleBadge({ style }: RunningStyleBadgeProps) {
  const colorClasses: Record<RunningStyle, string> = {
    ESCAPE: 'bg-red-100 text-red-800',
    FRONT: 'bg-orange-100 text-orange-800',
    STALKER: 'bg-yellow-100 text-yellow-800',
    CLOSER: 'bg-blue-100 text-blue-800',
    VERSATILE: 'bg-purple-100 text-purple-800',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClasses[style]}`}
    >
      {RUNNING_STYLE_LABELS[style]}
    </span>
  );
}

interface WorkoutBadgeProps {
  evaluation: WorkoutEvaluation;
}

export function WorkoutBadge({ evaluation }: WorkoutBadgeProps) {
  const colorClasses: Record<WorkoutEvaluation, string> = {
    A: 'bg-green-100 text-green-800',
    B: 'bg-blue-100 text-blue-800',
    C: 'bg-yellow-100 text-yellow-800',
    D: 'bg-gray-100 text-gray-800',
  };

  return (
    <span
      className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${colorClasses[evaluation]}`}
    >
      {evaluation}
    </span>
  );
}

interface CourseTypeBadgeProps {
  type: '芝' | 'ダート';
}

export function CourseTypeBadge({ type }: CourseTypeBadgeProps) {
  const isGrass = type === '芝';

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
        isGrass ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'
      }`}
    >
      {type}
    </span>
  );
}
