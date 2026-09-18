import { SignIn } from "@clerk/nextjs";

/**
 * The only real login surface in the product (roadmap P10 COPPA design: a
 * parent signs in; the child plays under that session -- there is no
 * separate child account to authenticate). Clerk's hosted `<SignIn>`
 * component, not a hand-rolled form -- P15 is an integration phase, not an
 * auth-UI phase.
 */
export default function SignInPage() {
  return (
    <div className="flex justify-center py-8">
      <SignIn />
    </div>
  );
}
