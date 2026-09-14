import React, { useState } from 'react';

interface FriendLobbyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEnterRoom: (roomCode: string, token: string, participant: 'A' | 'B') => void;
}

type LobbyTab = 'CREATE' | 'JOIN';

export const FriendLobbyModal: React.FC<FriendLobbyModalProps> = ({
  isOpen,
  onClose,
  onEnterRoom,
}) => {
  const [tab, setTab] = useState<LobbyTab>('CREATE');
  const [roomCodeInput, setRoomCodeInput] = useState<string>('');
  const [createdRoomCode, setCreatedRoomCode] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  if (!isOpen) return null;

  const handleCreateRoom = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch('/api/rooms', { method: 'POST' });
      if (!res.ok) throw new Error('Failed to create room.');
      const data = await res.json();
      setCreatedRoomCode(data.room_code);
      onEnterRoom(data.room_code, data.player_token, 'A');
    } catch (err: any) {
      setErrorMsg(err.message || 'Error creating room.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleJoinRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    const code = roomCodeInput.trim().toUpperCase();
    if (code.length !== 6) {
      setErrorMsg('Please enter a valid 6-character room code.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`/api/rooms/${code}/join`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) {
        const detail = data.detail;
        if (detail?.code === 'room_full') {
          throw new Error('This room is already full.');
        }
        if (detail?.code === 'room_not_found') {
          throw new Error('Room not found. Please check the code.');
        }
        throw new Error(detail?.message || 'Unable to join room.');
      }
      onEnterRoom(data.room_code, data.player_token, 'B');
    } catch (err: any) {
      setErrorMsg(err.message || 'Error joining room.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    if (createdRoomCode) {
      navigator.clipboard.writeText(createdRoomCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in select-none">
      <div className="relative w-full max-w-md bg-gradient-to-b from-slate-900 to-slate-950 border-2 border-amber-400/50 rounded-3xl p-6 sm:p-7 shadow-[0_0_50px_rgba(245,158,11,0.25)] text-white">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-9 h-9 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-slate-300 font-bold transition-colors"
          aria-label="Close"
        >
          ✕
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3 pb-4 border-b border-white/10">
          <div className="w-12 h-12 rounded-2xl bg-amber-400/20 border border-amber-400/40 flex items-center justify-center text-2xl shadow-inner">
            👥
          </div>
          <div>
            <h3 className="text-xl sm:text-2xl font-black text-amber-300 font-sans tracking-tight">
              Play with Friend
            </h3>
            <p className="text-xs text-slate-400">Head-to-head live Hand Cricket</p>
          </div>
        </div>

        {/* Tabs */}
        {!createdRoomCode && (
          <div className="flex p-1 bg-slate-950/80 rounded-xl border border-white/10 my-5">
            <button
              onClick={() => { setTab('CREATE'); setErrorMsg(null); }}
              className={`flex-1 py-2 rounded-lg font-black text-xs tracking-wider transition-all uppercase ${
                tab === 'CREATE'
                  ? 'bg-amber-400 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Create Room
            </button>
            <button
              onClick={() => { setTab('JOIN'); setErrorMsg(null); }}
              className={`flex-1 py-2 rounded-lg font-black text-xs tracking-wider transition-all uppercase ${
                tab === 'JOIN'
                  ? 'bg-amber-400 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Join Room
            </button>
          </div>
        )}

        {/* Error Notification */}
        {errorMsg && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/15 border border-red-400/30 text-red-300 text-xs font-bold text-center animate-shake">
            {errorMsg}
          </div>
        )}

        {/* Tab 1: Create Room */}
        {tab === 'CREATE' && (
          <div>
            {!createdRoomCode ? (
              <div className="flex flex-col items-center text-center py-4 space-y-4">
                <p className="text-sm text-slate-300 leading-relaxed max-w-xs">
                  Create a custom room and share your unique 6-character match code with your friend.
                </p>
                <button
                  onClick={handleCreateRoom}
                  disabled={isLoading}
                  className="w-full py-3.5 rounded-xl bg-gradient-to-r from-amber-400 via-amber-500 to-amber-400 text-slate-950 font-black text-sm uppercase tracking-wider shadow-lg shadow-amber-500/25 hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-50"
                >
                  {isLoading ? 'Creating Room...' : 'CREATE MATCH ROOM 🏏'}
                </button>
              </div>
            ) : (
              <div className="flex flex-col items-center text-center py-3 space-y-4">
                <span className="text-xs font-bold text-amber-400 uppercase tracking-widest">
                  ROOM CODE CREATED
                </span>
                <div className="px-6 py-3 rounded-2xl bg-black/60 border-2 border-amber-400/80 font-mono text-3xl sm:text-4xl font-black tracking-widest text-amber-300 shadow-inner">
                  {createdRoomCode}
                </div>
                <button
                  onClick={handleCopy}
                  className="text-xs font-bold text-slate-300 hover:text-white px-4 py-2 rounded-lg bg-white/10 hover:bg-white/15 transition-colors flex items-center gap-1.5"
                >
                  <span>{copied ? '✓ COPIED!' : '📋 Copy Code'}</span>
                </button>
                <p className="text-xs text-slate-400 animate-pulse mt-2">
                  Waiting for your friend to enter this code...
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Join Room */}
        {tab === 'JOIN' && (
          <form onSubmit={handleJoinRoom} className="space-y-4 py-2">
            <div>
              <label className="block text-xs font-bold text-slate-300 mb-2 uppercase tracking-wide">
                Enter 6-Letter Room Code:
              </label>
              <input
                type="text"
                value={roomCodeInput}
                onChange={(e) => setRoomCodeInput(e.target.value.toUpperCase())}
                placeholder="e.g. CRIC88"
                maxLength={6}
                autoFocus
                className="w-full px-4 py-3 rounded-xl bg-black/50 border-2 border-white/20 focus:border-amber-400 font-mono text-center text-2xl font-black tracking-widest text-white uppercase focus:outline-none transition-colors"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || roomCodeInput.trim().length !== 6}
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-amber-400 via-amber-500 to-amber-400 text-slate-950 font-black text-sm uppercase tracking-wider shadow-lg shadow-amber-500/25 hover:brightness-110 active:scale-[0.98] transition-all disabled:opacity-50"
            >
              {isLoading ? 'Joining Match...' : 'JOIN MATCH →'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
