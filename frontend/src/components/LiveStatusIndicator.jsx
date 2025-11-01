import React, { useState, useEffect, useRef } from 'react';
import { Activity, Wifi, WifiOff, Loader2 } from 'lucide-react';

const LiveStatusIndicator = ({ projectId, userId, onUpdate }) => {
  const [connected, setConnected] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [projectId]);

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/ws/${projectId}`;

    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
      setReconnecting(false);
      ws.send(JSON.stringify({ type: 'auth', user_id: userId }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'document_update') {
        onUpdate?.(data);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
      
      // Attempt to reconnect after 3 seconds
      setReconnecting(true);
      reconnectTimeoutRef.current = setTimeout(() => {
        connectWebSocket();
      }, 3000);
    };

    wsRef.current = ws;
  };

  return (
    <div className="flex items-center gap-2">
      {connected ? (
        <>
          <div className="relative">
            <Wifi className="w-4 h-4 text-emerald-400" />
            <div className="absolute -top-1 -right-1 w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
          </div>
          <span className="text-xs text-emerald-400 font-medium">Live</span>
        </>
      ) : reconnecting ? (
        <>
          <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
          <span className="text-xs text-yellow-400 font-medium">Reconnecting...</span>
        </>
      ) : (
        <>
          <WifiOff className="w-4 h-4 text-red-400" />
          <span className="text-xs text-red-400 font-medium">Disconnected</span>
        </>
      )}
    </div>
  );
};

export default LiveStatusIndicator;