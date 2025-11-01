import React, { useState, useRef, useEffect } from 'react';
import { 
  MessageSquare, Send, Loader2, FileText, Sparkles,
  ChevronDown, Copy, ThumbsUp, ThumbsDown, X,
  Settings, Zap, Brain, Search, AlertCircle
} from 'lucide-react';

const ChatInterface = ({ projectId, userId, apiClient }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [settings, setSettings] = useState({
    k: 5,
    temperature: 0.7
  });
  const [showSettings, setShowSettings] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await apiClient.request('/chat', {
        method: 'POST',
        body: JSON.stringify({
          query: input,
          project_id: projectId,
          user_id: userId,
          conversation_id: conversationId,
          k: settings.k,
          temperature: settings.temperature
        })
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.response,
        sources: response.sources,
        timestamp: response.timestamp
      };

      setMessages(prev => [...prev, assistantMessage]);
      
      if (!conversationId) {
        setConversationId(response.conversation_id);
      }

    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        error: true,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const clearChat = () => {
    if (window.confirm('Clear all messages?')) {
      setMessages([]);
      setConversationId(null);
    }
  };

  const suggestedQuestions = [
    "What are the main topics in these documents?",
    "Summarize the key findings",
    "What are the most important dates mentioned?",
    "Extract all numerical data and statistics"
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] bg-slate-900/50 backdrop-blur-xl border border-slate-800/50 rounded-2xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/50">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-pink-500/20 to-purple-500/20 rounded-xl">
            <MessageSquare className="w-5 h-5 text-pink-400" />
          </div>
          <div>
            <h3 className="font-bold">Chat with Documents</h3>
            <p className="text-xs text-slate-400">
              AI-powered answers from your knowledge base
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 hover:bg-slate-800/50 rounded-lg transition-all"
            title="Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
          <button
            onClick={clearChat}
            className="p-2 hover:bg-slate-800/50 rounded-lg transition-all text-slate-400 hover:text-red-400"
            title="Clear chat"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="px-6 py-4 bg-slate-800/30 border-b border-slate-800/50 space-y-3">
          <div>
            <label className="text-xs text-slate-400 mb-2 block">
              Sources to retrieve (k): {settings.k}
            </label>
            <input
              type="range"
              min="1"
              max="20"
              value={settings.k}
              onChange={(e) => setSettings({ ...settings, k: parseInt(e.target.value) })}
              className="w-full"
            />
          </div>
          <div>
            <label className="text-xs text-slate-400 mb-2 block">
              Creativity (temperature): {settings.temperature}
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.1"
              value={settings.temperature}
              onChange={(e) => setSettings({ ...settings, temperature: parseFloat(e.target.value) })}
              className="w-full"
            />
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="p-6 bg-gradient-to-br from-pink-500/10 to-purple-500/10 rounded-3xl mb-6">
              <Brain className="w-16 h-16 text-pink-400" />
            </div>
            <h3 className="text-xl font-bold mb-2">Ask me anything</h3>
            <p className="text-slate-400 mb-6 max-w-md">
              I can help you find information, summarize content, and answer questions about your documents.
            </p>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
              {suggestedQuestions.map((question, i) => (
                <button
                  key={i}
                  onClick={() => setInput(question)}
                  className="text-left p-4 bg-slate-800/30 hover:bg-slate-800/50 border border-slate-700/30 hover:border-slate-600 rounded-xl transition-all group"
                >
                  <div className="flex items-start gap-2">
                    <Sparkles className="w-4 h-4 text-pink-400 mt-1 flex-shrink-0" />
                    <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
                      {question}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <div
                key={index}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[80%] ${
                  message.role === 'user'
                    ? 'bg-gradient-to-r from-blue-500/20 to-purple-500/20 border border-blue-500/30'
                    : message.error
                    ? 'bg-red-500/10 border border-red-500/30'
                    : 'bg-slate-800/50 border border-slate-700/50'
                } rounded-2xl p-4 ${message.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'}`}>
                  
                  {/* Message Content */}
                  <div className="prose prose-invert prose-sm max-w-none">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {message.content}
                    </p>
                  </div>

                  {/* Sources */}
                  {message.sources && message.sources.length > 0 && (
                    <div className="mt-4 pt-4 border-t border-slate-700/50">
                      <div className="flex items-center gap-2 mb-3">
                        <Search className="w-3 h-3 text-slate-400" />
                        <span className="text-xs text-slate-400 font-medium">
                          Sources ({message.sources.length})
                        </span>
                      </div>
                      <div className="space-y-2">
                        {message.sources.slice(0, 3).map((source, i) => (
                          <div
                            key={i}
                            className="bg-slate-700/30 rounded-lg p-3 border border-slate-600/30 hover:border-slate-500/50 transition-all cursor-pointer"
                          >
                            <div className="flex items-start justify-between gap-2 mb-2">
                              <div className="flex items-center gap-2 flex-1 min-w-0">
                                <FileText className="w-3 h-3 text-pink-400 flex-shrink-0" />
                                <span className="text-xs font-medium truncate">
                                  {source.filename}
                                </span>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                {source.page && (
                                  <span className="text-xs text-slate-400">p. {source.page}</span>
                                )}
                                <div className="px-2 py-0.5 bg-emerald-500/20 border border-emerald-500/30 rounded text-xs font-medium text-emerald-400">
                                  {(source.similarity * 100).toFixed(0)}%
                                </div>
                              </div>
                            </div>
                            <p className="text-xs text-slate-400 line-clamp-2">
                              {source.preview}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Message Actions */}
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-700/30">
                    <span className="text-xs text-slate-500">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </span>
                    {message.role === 'assistant' && !message.error && (
                      <>
                        <div className="flex-1" />
                        <button
                          onClick={() => copyToClipboard(message.content)}
                          className="p-1 hover:bg-slate-700/50 rounded transition-all"
                          title="Copy"
                        >
                          <Copy className="w-3 h-3" />
                        </button>
                        <button className="p-1 hover:bg-slate-700/50 rounded transition-all" title="Good response">
                          <ThumbsUp className="w-3 h-3" />
                        </button>
                        <button className="p-1 hover:bg-slate-700/50 rounded transition-all" title="Bad response">
                          <ThumbsDown className="w-3 h-3" />
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}

            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-slate-800/50 border border-slate-700/50 rounded-2xl rounded-tl-sm p-4 flex items-center gap-3">
                  <Loader2 className="w-4 h-4 animate-spin text-pink-400" />
                  <span className="text-sm text-slate-400">Thinking...</span>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-6 py-4 border-t border-slate-800/50">
        <div className="flex items-end gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your documents..."
              rows="1"
              className="w-full px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-xl focus:outline-none focus:border-pink-500/50 resize-none transition-all"
              style={{ minHeight: '44px', maxHeight: '120px' }}
            />
          </div>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="p-3 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl transition-all shadow-lg shadow-pink-500/25"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        <p className="text-xs text-slate-500 mt-2">
          Press Enter to send, Shift+Enter for new line
        </p>
      </div>
    </div>
  );
};

export default ChatInterface;