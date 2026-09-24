"use client";

import { useState, useEffect, useRef } from "react";
import { Bell, Check, Trash2, Mail, Bot, FileText, AlertTriangle } from "lucide-react";
import { apiFetch, apiPost, apiDelete } from "@/lib/api";
import { toast } from "react-hot-toast";

interface NotificationItem {
  id: number;
  type: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export function Header() {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      const data = await apiFetch<NotificationItem[]>("/api/v1/notifications/");
      setNotifications(data);
    } catch (e) {
      console.error("Failed to fetch notifications:", e);
    }
  };

  useEffect(() => {
    fetchNotifications();
    // Poll notifications every 10 seconds for real-time updates
    const interval = setInterval(fetchNotifications, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleMarkRead = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiPost(`/api/v1/notifications/${id}/read`);
      setNotifications(notifications.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    } catch (e) {
      toast.error("Failed to mark as read");
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiPost("/api/v1/notifications/read-all");
      setNotifications(notifications.map((n) => ({ ...n, is_read: true })));
      toast.success("All notifications marked as read");
    } catch (e) {
      toast.error("Failed to mark all as read");
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiDelete(`/api/v1/notifications/${id}`);
      setNotifications(notifications.filter((n) => n.id !== id));
    } catch (e) {
      toast.error("Failed to delete notification");
    }
  };

  const getNotifIcon = (type: string) => {
    switch (type) {
      case "resume_generated":
        return <FileText className="text-blue-500" size={14} />;
      case "application_completed":
        return <Bot className="text-emerald-500" size={14} />;
      case "error":
        return <AlertTriangle className="text-amber-500" size={14} />;
      default:
        return <Bell className="text-zinc-500" size={14} />;
    }
  };

  return (
    <header className="h-14 border-b border-zinc-200/50 flex items-center justify-end px-8 bg-white relative">
      <div ref={dropdownRef} className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="relative p-2 text-zinc-400 hover:text-zinc-700 hover:bg-zinc-100 rounded-lg transition-all"
        >
          <Bell size={18} />
          {unreadCount > 0 && (
            <span className="absolute top-1.5 right-1.5 w-4 h-4 bg-indigo-600 text-[10px] font-bold text-white rounded-full flex items-center justify-center border border-white">
              {unreadCount}
            </span>
          )}
        </button>

        {isOpen && (
          <div className="absolute right-0 mt-2 w-80 bg-white border border-zinc-200 rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
            <div className="p-4 border-b border-zinc-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-zinc-900">Notifications</h3>
              {unreadCount > 0 && (
                <button
                  onClick={handleMarkAllRead}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1"
                >
                  <Check size={12} /> Mark all read
                </button>
              )}
            </div>

            <div className="max-h-[300px] overflow-y-auto divide-y divide-zinc-100">
              {notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={(e) => !notif.is_read && handleMarkRead(notif.id, e)}
                  className={`p-4 flex items-start gap-3 hover:bg-zinc-50 transition-colors cursor-pointer ${
                    !notif.is_read ? "bg-zinc-50/50" : ""
                  }`}
                >
                  <div className="w-6 h-6 rounded bg-zinc-100 flex items-center justify-center mt-0.5">
                    {getNotifIcon(notif.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-xs ${!notif.is_read ? "font-semibold text-zinc-900" : "text-zinc-600"}`}>
                      {notif.message}
                    </p>
                    <span className="text-[10px] text-zinc-400 mt-1 block">
                      {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <div className="flex flex-col gap-1 items-end">
                    {!notif.is_read && (
                      <button
                        onClick={(e) => handleMarkRead(notif.id, e)}
                        className="p-1 text-indigo-600 hover:bg-indigo-50 rounded"
                        title="Mark as read"
                      >
                        <Check size={12} />
                      </button>
                    )}
                    <button
                      onClick={(e) => handleDelete(notif.id, e)}
                      className="p-1 text-zinc-400 hover:text-red-600 hover:bg-red-50 rounded"
                      title="Delete"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              ))}

              {notifications.length === 0 && (
                <div className="p-8 text-center text-zinc-400 text-xs">
                  No notifications yet.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
