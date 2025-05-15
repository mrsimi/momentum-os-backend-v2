# from schemas.checkin_response_schema import CheckInAnalyticsRequest
# from services.ai_service import AiService


if __name__ == "__main__":
    import socket
    print(socket.gethostname())

    
    # ai_service = AiService()
    # response = [
    #     CheckInAnalyticsRequest(
    #         did_yesterday="""
    # I finished the entire onboarding flow for new users — including the welcome screen, email confirmation step, and basic profile setup. 
    # Also spent quite a bit of time talking to two early adopters on Discord. They gave me some great feedback on how confusing the referral instructions were.
    # To end the day, I rewrote the pricing page copy to make it feel more personal and aligned with our tone — something fun but still professional.
    # """,
    #             doing_today="""
    # Today I'm focusing on integrating the referral system. 
    # I’ve sketched out how I want the invite flow to look, but I’m not sure yet how to track referrals correctly — might explore using unique invite tokens or something similar. 
    # If I get through that, I’ll also be testing the dashboard on mobile to make sure it doesn’t break anything visually.
    # """,
    #             blockers="""
    # Still trying to wrap my head around referral attribution. It’s not super clear how to track multiple invites from the same person. 
    # Also, Discord is a bit distracting during deep work hours 😅.
    # """,
    #             email="jane@example.com", team_member_id=1
    #         ),
    #         CheckInAnalyticsRequest(
    #             did_yesterday="""
    # I completed the Zapier integration — finally! It took longer than I expected because of some weird edge cases around webhook retries. 
    # Also set up a temporary staging environment so I can test integrations without breaking anything live. 
    # In between, I answered a bunch of questions from a few beta users who were confused about setting up their first automation — noted those issues for our onboarding improvements.
    # """,
    #             doing_today="""
    # Today I’ll be focusing on writing proper documentation for the Zapier workflows.
    # Not just technical docs, but step-by-step guides that non-technical users can follow.
    # If I have time left, I’ll look at the new Notion API changes — I think there's potential to make that a lot smoother for our users.
    # """,
    #             blockers="""
    # Docs are always slower than I plan for. 
    # Also slightly blocked by lack of real user examples to make the guides more relatable.
    # """,
    #             email="devguy@example.com", team_member_id=2
    #         )
    #     ]

    # product_description = """
    # We are building a creator-focused platform that lets people automate their work, sell digital products, and monitor performance — all without writing code.
    # Our core features include seamless integrations with tools like Zapier and Notion, a user-friendly dashboard, and an invite-based referral system to help drive growth.
    # The target audience includes solo creators, indie consultants, and educators who want to focus on content, not complexity.
    # """

    # ai_service.process_response(response, product_description)
