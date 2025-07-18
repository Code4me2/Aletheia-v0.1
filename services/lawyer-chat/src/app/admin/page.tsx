'use client';

import { useEffect, useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useSidebarStore } from '@/store/sidebar';
import DarkModeToggle from '@/components/DarkModeToggle';
import { Users, Shield, Activity, AlertTriangle, Download, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import { getApiEndpoint } from '@/lib/api-config';

interface UserData {
  id: string;
  email: string;
  name: string;
  emailVerified: Date | null;
  createdAt: Date;
  lastLoginAt: Date | null;
  lastLoginIp: string | null;
  failedLoginAttempts: number;
  lockedUntil: Date | null;
  role: string;
}

interface AuditLog {
  id: string;
  action: string;
  email: string | null;
  ipAddress: string | null;
  success: boolean;
  errorMessage: string | null;
  createdAt: Date;
}

export default function AdminDashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const { isDarkMode } = useSidebarStore();
  const [users, setUsers] = useState<UserData[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [stats, setStats] = useState({
    totalUsers: 0,
    verifiedUsers: 0,
    lockedAccounts: 0,
    recentRegistrations: 0
  });
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'users' | 'activity'>('users');

  useEffect(() => {
    if (status === 'loading') return;
    
    // Check if user is admin
    if (!session || session.user.role !== 'admin') {
      router.push('/');
      return;
    }

    fetchData();
  }, [session, status, router]);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      // Fetch users
      const usersRes = await fetch(`/chat${getApiEndpoint('/admin/users')}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (!usersRes.ok) {
        throw new Error(`Failed to fetch users: ${usersRes.status} ${usersRes.statusText}`);
      }
      
      const usersData = await usersRes.json();
      
      if (Array.isArray(usersData)) {
        setUsers(usersData);

        // Calculate stats
        const verified = usersData.filter((u: UserData) => u.emailVerified).length;
        const locked = usersData.filter((u: UserData) => u.lockedUntil && new Date(u.lockedUntil) > new Date()).length;
        const recent = usersData.filter((u: UserData) => {
          const createdDate = new Date(u.createdAt);
          const weekAgo = new Date();
          weekAgo.setDate(weekAgo.getDate() - 7);
          return createdDate > weekAgo;
        }).length;

        setStats({
          totalUsers: usersData.length,
          verifiedUsers: verified,
          lockedAccounts: locked,
          recentRegistrations: recent
        });
      }

      // Fetch audit logs
      const logsRes = await fetch(`/chat${getApiEndpoint('/admin/audit-logs')}`, {
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      
      if (logsRes.ok) {
        const logsData = await logsRes.json();
        if (Array.isArray(logsData)) {
          setAuditLogs(logsData);
        }
      }
    } catch (error) {
      console.error('Error fetching admin data:', error);
      // Show error to user
      alert('Failed to load admin data. Please check the console for details.');
    } finally {
      setIsLoading(false);
    }
  };

  const exportUsers = () => {
    const csv = [
      ['Email', 'Name', 'Verified', 'Created At', 'Last Login', 'Status'].join(','),
      ...users.map(user => [
        user.email,
        user.name || '',
        user.emailVerified ? 'Yes' : 'No',
        format(new Date(user.createdAt), 'yyyy-MM-dd'),
        user.lastLoginAt ? format(new Date(user.lastLoginAt), 'yyyy-MM-dd HH:mm') : 'Never',
        user.lockedUntil && new Date(user.lockedUntil) > new Date() ? 'Locked' : 'Active'
      ].join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `users-export-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
  };

  if (status === 'loading' || isLoading) {
    return (
      <div className={`min-h-screen ${isDarkMode ? 'bg-[#1a1b1e]' : 'bg-gray-50'} flex items-center justify-center`}>
        <div className={`w-8 h-8 border-2 ${isDarkMode ? 'border-gray-400' : 'border-blue-600'} border-t-transparent rounded-full animate-spin`}></div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-[#1a1b1e]' : 'bg-gray-50'}`}>
      {/* Header */}
      <div className={`${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} border-b`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between py-4">
            <div className="flex items-center gap-3">
              <Shield className={isDarkMode ? 'text-gray-400' : 'text-gray-600'} size={24} />
              <h1 className={`text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                Admin Dashboard
              </h1>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={fetchData}
                className={`p-2 rounded-lg transition-colors ${
                  isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'
                }`}
                aria-label="Refresh data"
                title="Refresh data"
              >
                <RefreshCw size={20} className={isDarkMode ? 'text-gray-400' : 'text-gray-600'} />
              </button>
              <DarkModeToggle />
            </div>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} border`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Total Users
                </p>
                <p className={`text-3xl font-bold mt-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  {stats.totalUsers}
                </p>
              </div>
              <Users className={isDarkMode ? 'text-gray-600' : 'text-gray-400'} size={32} />
            </div>
          </div>

          <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} border`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Verified Users
                </p>
                <p className={`text-3xl font-bold mt-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  {stats.verifiedUsers}
                </p>
              </div>
              <Shield className="text-green-500" size={32} />
            </div>
          </div>

          <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} border`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  Locked Accounts
                </p>
                <p className={`text-3xl font-bold mt-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  {stats.lockedAccounts}
                </p>
              </div>
              <AlertTriangle className="text-red-500" size={32} />
            </div>
          </div>

          <div className={`p-6 rounded-lg ${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} border`}>
            <div className="flex items-center justify-between">
              <div>
                <p className={`text-sm font-medium ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                  New This Week
                </p>
                <p className={`text-3xl font-bold mt-2 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  {stats.recentRegistrations}
                </p>
              </div>
              <Activity className="text-blue-500" size={32} />
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className={`${isDarkMode ? 'bg-[#25262b] border-gray-700' : 'bg-white border-gray-200'} rounded-lg border`}>
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex">
              <button
                onClick={() => setActiveTab('users')}
                className={`py-4 px-8 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'users'
                    ? isDarkMode
                      ? 'border-[#C7A562] text-[#C7A562]'
                      : 'border-[#004A84] text-[#004A84]'
                    : isDarkMode
                      ? 'border-transparent text-gray-400 hover:text-gray-300'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Users
              </button>
              <button
                onClick={() => setActiveTab('activity')}
                className={`py-4 px-8 font-medium text-sm border-b-2 transition-colors ${
                  activeTab === 'activity'
                    ? isDarkMode
                      ? 'border-[#C7A562] text-[#C7A562]'
                      : 'border-[#004A84] text-[#004A84]'
                    : isDarkMode
                      ? 'border-transparent text-gray-400 hover:text-gray-300'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Activity Logs
              </button>
            </nav>
          </div>

          {/* Content */}
          <div className="p-6">
            {activeTab === 'users' ? (
              <>
                <div className="flex justify-between items-center mb-4">
                  <h2 className={`text-lg font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                    Registered Users
                  </h2>
                  <button
                    onClick={exportUsers}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isDarkMode
                        ? 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    <Download size={16} />
                    Export CSV
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className={`border-b ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                        <th className={`text-left py-3 px-4 font-medium text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Email
                        </th>
                        <th className={`text-left py-3 px-4 font-medium text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Name
                        </th>
                        <th className={`text-left py-3 px-4 font-medium text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Status
                        </th>
                        <th className={`text-left py-3 px-4 font-medium text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Created
                        </th>
                        <th className={`text-left py-3 px-4 font-medium text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                          Last Login
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user) => (
                        <tr key={user.id} className={`border-b ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                          <td className={`py-3 px-4 ${isDarkMode ? 'text-gray-300' : 'text-gray-900'}`}>
                            {user.email}
                          </td>
                          <td className={`py-3 px-4 ${isDarkMode ? 'text-gray-300' : 'text-gray-900'}`}>
                            {user.name || '-'}
                          </td>
                          <td className="py-3 px-4">
                            {user.lockedUntil && new Date(user.lockedUntil) > new Date() ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                Locked
                              </span>
                            ) : user.emailVerified ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                Verified
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                Unverified
                              </span>
                            )}
                          </td>
                          <td className={`py-3 px-4 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            {format(new Date(user.createdAt), 'MMM d, yyyy')}
                          </td>
                          <td className={`py-3 px-4 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            {user.lastLoginAt 
                              ? format(new Date(user.lastLoginAt), 'MMM d, yyyy HH:mm')
                              : 'Never'
                            }
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : (
              <>
                <h2 className={`text-lg font-semibold mb-4 ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
                  Recent Activity
                </h2>

                <div className="space-y-2">
                  {auditLogs.map((log) => (
                    <div
                      key={log.id}
                      className={`p-4 rounded-lg border ${
                        isDarkMode ? 'bg-[#1a1b1e] border-gray-700' : 'bg-gray-50 border-gray-200'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className={`font-medium ${
                              log.success 
                                ? isDarkMode ? 'text-green-400' : 'text-green-600'
                                : isDarkMode ? 'text-red-400' : 'text-red-600'
                            }`}>
                              {log.action}
                            </span>
                            {log.email && (
                              <span className={`text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                                • {log.email}
                              </span>
                            )}
                          </div>
                          {log.errorMessage && (
                            <p className={`text-sm mt-1 ${isDarkMode ? 'text-gray-500' : 'text-gray-500'}`}>
                              {log.errorMessage}
                            </p>
                          )}
                          <div className={`flex items-center gap-4 mt-2 text-xs ${
                            isDarkMode ? 'text-gray-500' : 'text-gray-400'
                          }`}>
                            <span>IP: {log.ipAddress || 'Unknown'}</span>
                            <span>{format(new Date(log.createdAt), 'MMM d, yyyy HH:mm:ss')}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}