import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useCreateRace, useCreateHorse } from '../hooks';
import type { RaceCreate, HorseCreate, Grade, CourseType } from '../types';
import { VENUES } from '../types';

export function DataInput() {
  const [activeTab, setActiveTab] = useState<'race' | 'horse'>('race');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">データ入力</h1>
        <p className="mt-1 text-gray-500">レースや出走馬のデータを手動で登録</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('race')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'race'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            レース登録
          </button>
          <button
            onClick={() => setActiveTab('horse')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'horse'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            馬登録
          </button>
        </nav>
      </div>

      {/* Content */}
      {activeTab === 'race' ? <RaceForm /> : <HorseForm />}
    </div>
  );
}

function RaceForm() {
  const createRace = useCreateRace();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<RaceCreate>();

  const onSubmit = async (data: RaceCreate) => {
    try {
      await createRace.mutateAsync(data);
      reset();
      alert('レースを登録しました');
    } catch (error) {
      alert('登録に失敗しました');
    }
  };

  const grades: Grade[] = ['G1', 'G2', 'G3', 'OP', 'L'];
  const courseTypes: CourseType[] = ['芝', 'ダート'];

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">レース名 *</label>
          <input
            {...register('name', { required: 'レース名は必須です' })}
            className="input"
            placeholder="日本ダービー"
          />
          {errors.name && (
            <p className="text-red-500 text-sm mt-1">{errors.name.message}</p>
          )}
        </div>

        <div>
          <label className="label">開催日 *</label>
          <input
            {...register('date', { required: '開催日は必須です' })}
            type="date"
            className="input"
          />
          {errors.date && (
            <p className="text-red-500 text-sm mt-1">{errors.date.message}</p>
          )}
        </div>

        <div>
          <label className="label">競馬場 *</label>
          <select
            {...register('venue', { required: '競馬場は必須です' })}
            className="input"
          >
            <option value="">選択してください</option>
            {VENUES.map((venue) => (
              <option key={venue} value={venue}>
                {venue}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">グレード *</label>
          <select
            {...register('grade', { required: 'グレードは必須です' })}
            className="input"
          >
            <option value="">選択してください</option>
            {grades.map((grade) => (
              <option key={grade} value={grade}>
                {grade}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">コース *</label>
          <select
            {...register('course_type', { required: 'コースは必須です' })}
            className="input"
          >
            <option value="">選択してください</option>
            {courseTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">距離 (m) *</label>
          <input
            {...register('distance', {
              required: '距離は必須です',
              valueAsNumber: true,
              min: { value: 800, message: '800m以上で入力してください' },
              max: { value: 4000, message: '4000m以下で入力してください' },
            })}
            type="number"
            className="input"
            placeholder="2400"
          />
          {errors.distance && (
            <p className="text-red-500 text-sm mt-1">{errors.distance.message}</p>
          )}
        </div>

        <div>
          <label className="label">賞金 (万円)</label>
          <input
            {...register('purse', { valueAsNumber: true })}
            type="number"
            className="input"
            placeholder="30000"
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={createRace.isPending}
          className="btn btn-primary"
        >
          {createRace.isPending ? '登録中...' : 'レースを登録'}
        </button>
      </div>
    </form>
  );
}

function HorseForm() {
  const createHorse = useCreateHorse();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<HorseCreate>();

  const onSubmit = async (data: HorseCreate) => {
    try {
      await createHorse.mutateAsync(data);
      reset();
      alert('馬を登録しました');
    } catch (error) {
      alert('登録に失敗しました');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="card space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label">馬名 *</label>
          <input
            {...register('name', { required: '馬名は必須です' })}
            className="input"
            placeholder="ディープインパクト"
          />
          {errors.name && (
            <p className="text-red-500 text-sm mt-1">{errors.name.message}</p>
          )}
        </div>

        <div>
          <label className="label">馬齢</label>
          <input
            {...register('age', { valueAsNumber: true })}
            type="number"
            className="input"
            placeholder="3"
          />
        </div>

        <div>
          <label className="label">性別</label>
          <select {...register('sex')} className="input">
            <option value="">選択してください</option>
            <option value="牡">牡</option>
            <option value="牝">牝</option>
            <option value="セ">セ</option>
          </select>
        </div>

        <div>
          <label className="label">調教師</label>
          <input
            {...register('trainer')}
            className="input"
            placeholder="池江泰寿"
          />
        </div>

        <div className="md:col-span-2">
          <label className="label">馬主</label>
          <input
            {...register('owner')}
            className="input"
            placeholder="金子真人ホールディングス"
          />
        </div>
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={createHorse.isPending}
          className="btn btn-primary"
        >
          {createHorse.isPending ? '登録中...' : '馬を登録'}
        </button>
      </div>
    </form>
  );
}
