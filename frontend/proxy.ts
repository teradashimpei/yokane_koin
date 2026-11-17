import { NextRequest, NextResponse } from "next/server";

// /staff 以下はログイン Cookie がなければ P1 へ(署名の確認は BFF と backend で行う)
export function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (pathname === "/") return NextResponse.redirect(new URL("/staff", req.url));
  if (pathname.startsWith("/staff") && pathname !== "/staff/login" && !req.cookies.get("yk_staff")) {
    return NextResponse.redirect(new URL("/staff/login", req.url));
  }
  return NextResponse.next();
}

export const config = { matcher: ["/", "/staff/:path*"] };
