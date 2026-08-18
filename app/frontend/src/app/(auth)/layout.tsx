export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-navy to-navy-dark p-5">
      <div className="w-full max-w-[440px] rounded-[14px] bg-white p-[38px] shadow-[0_20px_60px_rgba(0,0,0,0.3)]">
        {children}
      </div>
    </div>
  );
}
