"""Chat views — proxies user messages to OpenAI's chat completions API."""

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from openai import OpenAI

REGION_DESCRIPTIONS = {
    'uk': (
        'United Kingdom',
        (
            'Account types: ISA (Individual Savings Account), SIPP (Self-Invested Personal Pension), GIA (General Investment Account). '
            'Regulatory body: FCA (Financial Conduct Authority). '
            'Tax authority: HMRC. '
            'Prices and values are in GBP (£). '
            'Relevant UK tax considerations include Capital Gains Tax (CGT) and Dividend Allowance.'
        ),
    ),
    'us': (
        'United States',
        (
            'Account types: 401(k), IRA (Traditional and Roth), brokerage accounts. '
            'Regulatory bodies: SEC (Securities and Exchange Commission) and FINRA. '
            'Tax authority: IRS. '
            'Prices and values are in USD ($). '
            'Relevant US tax considerations include capital gains tax rates, wash-sale rules, and contribution limits.'
        ),
    ),
    'europe': (
        'Europe (EU)',
        (
            'Account types: General EU investment accounts, pension schemes vary by country. '
            'Regulatory body: ESMA (European Securities and Markets Authority). '
            'Applicable regulation: MiFID II (Markets in Financial Instruments Directive). '
            'Prices and values are in EUR (€). '
            'Tax rules vary by EU member state; consider local tax advice.'
        ),
    ),
}

SYSTEM_PROMPT_TEMPLATE = """\
You are a helpful stock market and investment assistant for a personal portfolio dashboard called Stasha.
You help users understand their portfolio, stock prices, investment strategies, and financial calculations.
Region: {region_name}
{region_specific_rules}
IMPORTANT: You are NOT a financial advisor. Always caveat responses with this disclaimer where relevant.
Keep responses concise and practical.\
"""

DISCLAIMER = (
    "I'm an AI assistant, not a financial advisor. "
    "This is for informational purposes only."
)


def _build_system_prompt(region: str) -> str:
    region_name, region_rules = REGION_DESCRIPTIONS.get(
        region, REGION_DESCRIPTIONS['uk']
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        region_name=region_name,
        region_specific_rules=region_rules,
    )


class ChatView(APIView):
    """POST /api/chat/ — proxy a user message to OpenAI and return the reply."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        message = request.data.get('message', '').strip()
        context = request.data.get('context', {})
        history = request.data.get('history', [])  # list of {role, content} dicts

        if not message:
            return Response({'detail': 'Message required.'}, status=400)

        # Resolve user region from their profile (auto-created if absent).
        from apps.accounts.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        region = profile.region or 'uk'

        system_prompt = _build_system_prompt(region)

        # Build messages list: system → validated history → optional context → user message
        messages = [{"role": "system", "content": system_prompt}]

        # Append prior conversation turns (basic validation only)
        for turn in history:
            role = turn.get('role', '')
            content = turn.get('content', '')
            if role in ('user', 'assistant') and content:
                messages.append({"role": role, "content": str(content)})

        # If portfolio context was supplied, prepend it to the user message
        if context:
            import json
            context_text = f"Portfolio context:\n{json.dumps(context, indent=2)}\n\n"
            user_content = context_text + message
        else:
            user_content = message

        messages.append({"role": "user", "content": user_content})

        api_key = getattr(settings, 'OPENAI_API_KEY', '')
        if not api_key:
            return Response(
                {'detail': 'OpenAI API key is not configured on the server.'},
                status=503,
            )

        client = OpenAI(api_key=api_key)

        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
            )
        except Exception as exc:
            return Response({'detail': f'OpenAI error: {exc}'}, status=502)

        reply_text = completion.choices[0].message.content or ''

        # Append the disclaimer if it isn't already present in the reply
        if DISCLAIMER not in reply_text:
            reply_text = f"{reply_text}\n\n---\n{DISCLAIMER}"

        return Response({
            'reply': reply_text,
            'usage': {
                'prompt_tokens': completion.usage.prompt_tokens,
                'completion_tokens': completion.usage.completion_tokens,
                'total_tokens': completion.usage.total_tokens,
            },
        })
