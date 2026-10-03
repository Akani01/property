import os



import uuid



import logging



from decimal import Decimal, InvalidOperation







import requests



from django.conf import settings







from .external import ConfigurableExternalGateway











logger = logging.getLogger(__name__)











class YocoGateway(ConfigurableExternalGateway):



    """



    Yoco payment gateway for OppoGlobe Car Wash.







    Responsibilities:



    - Read Yoco keys from Django settings/environment



    - Create hosted Yoco checkouts



    - Convert Rand amounts to cents



    - Return a normalised result to the rest of the carwash app



    - Support refunds



    - Keep the secret key completely server-side







    IMPORTANT:



    Never expose YOCO_SECRET_KEY to templates or JavaScript.



    """







    code = "yoco"



    name = "Yoco"







    BASE_URL = "https://payments.yoco.com/api"







    supports_card = True



    supports_eft = False



    supports_wallet = False







    default_currency = "ZAR"







    # ============================================================



    # KEYS



    # ============================================================







    @property



    def public_key(self):



        """



        Public/test public key.







        This key may be exposed to the frontend if required,



        although the hosted checkout flow normally does not need it.



        """







        return (



            getattr(settings, "YOCO_PUBLIC_KEY", "")



            or os.getenv("YOCO_PUBLIC_KEY", "")



        ).strip()







    @property



    def secret_key(self):



        """



        Secret/test secret key.







        SERVER SIDE ONLY.



        """







        return (



            getattr(settings, "YOCO_SECRET_KEY", "")



            or os.getenv("YOCO_SECRET_KEY", "")



        ).strip()







    # ============================================================



    # CONFIGURATION



    # ============================================================







    def is_configured(self):



        """



        Check whether Yoco can be used.



        """







        return bool(self.secret_key)







    def configuration_status(self):



        """



        Helpful for displaying Yoco in your gateway API/dashboard.



        """







        return {



            "code": self.code,



            "name": self.name,







            "configured": self.is_configured(),







            "has_public_key": bool(



                self.public_key



            ),







            "has_secret_key": bool(



                self.secret_key



            ),







            "supports_card": (



                self.supports_card



            ),







            "supports_eft": (



                self.supports_eft



            ),







            "supports_wallet": (



                self.supports_wallet



            ),







            "currency": (



                self.default_currency



            ),



        }







    # ============================================================



    # INTERNAL HEADERS



    # ============================================================







    def _headers(



        self,



        idempotency_key=None,



    ):



        """



        Generate Yoco API request headers.



        """







        if not self.secret_key:







            raise ValueError(



                "Yoco secret key "



                "is not configured."



            )







        headers = {







            "Authorization": (



                f"Bearer "



                f"{self.secret_key}"



            ),







            "Content-Type": (



                "application/json"



            ),







            "Accept": (



                "application/json"



            ),



        }







        if idempotency_key:







            headers[



                "Idempotency-Key"



            ] = str(



                idempotency_key



            )







        return headers







    # ============================================================



    # AMOUNT HELPERS



    # ============================================================







    @staticmethod



    def amount_to_cents(



        amount,



    ):



        """



        Convert Rand to cents.







        Examples:







        R1.00   -> 100



        R50.00  -> 5000



        R150.50 -> 15050



        """







        try:







            value = Decimal(



                str(amount)



            )







        except (



            InvalidOperation,



            TypeError,



            ValueError,



        ):







            raise ValueError(



                "Invalid payment amount."



            )







        if value <= 0:







            raise ValueError(



                "Payment amount must "



                "be greater than zero."



            )







        cents = (



            value



            * Decimal("100")



        ).quantize(



            Decimal("1")



        )







        return int(cents)







    @staticmethod



    def cents_to_amount(



        cents,



    ):



        """



        Convert cents back to Rand.







        15000 -> Decimal('150.00')



        """







        try:







            return (



                Decimal(



                    str(cents)



                )



                / Decimal("100")



            ).quantize(



                Decimal("0.01")



            )







        except Exception:







            return Decimal(



                "0.00"



            )







    # ============================================================



    # REFERENCE



    # ============================================================







    @staticmethod



    def generate_reference():



        """



        Generate unique OppoGlobe payment reference.



        """







        return (



            "OPPO-CW-"



            + uuid.uuid4()



            .hex[:16]



            .upper()



        )







    # ============================================================



    # CREATE CHECKOUT



    # ============================================================







    def create_checkout(



        self,



        *,



        amount,



        success_url,



        cancel_url,



        failure_url=None,



        reference=None,



        metadata=None,



        currency="ZAR",



        idempotency_key=None,



    ):



        """



        Create a hosted Yoco checkout.







        Example:







        gateway = YocoGateway()







        result = gateway.create_checkout(



            amount=Decimal("150.00"),



            reference="CARWASH-123",



            success_url="https://oppoglobe.co.za",



            cancel_url="https://oppoglobe.co.za",



        )







        The customer should then be redirected to:







            result["redirect_url"]



        """







        if not self.is_configured():







            return {







                "success": False,







                "gateway": self.code,







                "error": (



                    "Yoco is not configured. "



                    "Please configure "



                    "YOCO_SECRET_KEY."



                ),



            }







        try:







            amount_cents = (



                self.amount_to_cents(



                    amount



                )



            )







        except ValueError as exc:







            return {







                "success": False,







                "gateway": self.code,







                "error": str(exc),



            }







        if not reference:







            reference = (



                self.generate_reference()



            )







        if not idempotency_key:







            idempotency_key = (



                str(



                    uuid.uuid4()



                )



            )







        checkout_metadata = {







            "reference": (



                str(reference)



            ),







            "platform": (



                "OppoGlobe"



            ),







            "module": (



                "carwash"



            ),



        }







        if metadata:







            for (



                key,



                value,



            ) in metadata.items():







                if value is None:



                    continue







                checkout_metadata[



                    str(key)



                ] = str(



                    value



                )







        payload = {







            "amount": (



                amount_cents



            ),







            "currency": (



                currency



            ),







            "successUrl": (



                success_url



            ),







            "cancelUrl": (



                cancel_url



            ),







            "metadata": (



                checkout_metadata



            ),



        }







        if failure_url:







            payload[



                "failureUrl"



            ] = (



                failure_url



            )







        try:







            response = (



                requests.post(



                    (



                        f"{self.BASE_URL}"



                        "/checkouts"



                    ),







                    headers=(



                        self._headers(



                            idempotency_key



                        )



                    ),







                    json=payload,







                    timeout=30,



                )



            )







        except (



            requests.Timeout



        ):







            logger.warning(



                "Yoco checkout "



                "request timed out."



            )







            return {







                "success": False,







                "gateway": self.code,







                "error": (



                    "Yoco did not respond "



                    "in time. Please try again."



                ),



            }







        except (



            requests.RequestException



        ) as exc:







            logger.exception(



                "Could not connect "



                "to Yoco."



            )







            return {







                "success": False,







                "gateway": self.code,







                "error": (



                    "Could not connect "



                    "to Yoco."



                ),







                "exception": (



                    str(exc)



                ),



            }







        try:







            data = (



                response.json()



            )







        except ValueError:







            data = {}







        # --------------------------------------------------------



        # FAILED



        # --------------------------------------------------------







        if not response.ok:







            logger.error(



                (



                    "Yoco checkout "



                    "failed. HTTP %s: %s"



                ),



                response.status_code,



                data,



            )







            error_message = (







                data.get(



                    "message"



                )







                or data.get(



                    "error"



                )







                or data.get(



                    "detail"



                )







                or (



                    "Yoco could not "



                    "create the checkout."



                )



            )







            return {







                "success": False,







                "gateway": (



                    self.code



                ),







                "error": (



                    error_message



                ),







                "status_code": (



                    response.status_code



                ),







                "response": (



                    data



                ),



            }







        # --------------------------------------------------------



        # SUCCESS



        # --------------------------------------------------------







        checkout_id = (







            data.get(



                "id"



            )







            or data.get(



                "checkoutId"



            )







            or data.get(



                "checkout_id"



            )



        )







        redirect_url = (







            data.get(



                "redirectUrl"



            )







            or data.get(



                "redirect_url"



            )







            or data.get(



                "url"



            )



        )







        if not redirect_url:







            logger.warning(



                (



                    "Yoco checkout created "



                    "but no redirect URL "



                    "was returned: %s"



                ),



                data,



            )







        return {







            "success": True,







            "gateway": (



                self.code



            ),







            "gateway_name": (



                self.name



            ),







            "checkout_id": (



                checkout_id



            ),







            "redirect_url": (



                redirect_url



            ),







            "reference": (



                reference



            ),







            "amount": str(



                Decimal(



                    str(amount)



                ).quantize(



                    Decimal(



                        "0.01"



                    )



                )



            ),







            "amount_cents": (



                amount_cents



            ),







            "currency": (



                currency



            ),







            "idempotency_key": (



                idempotency_key



            ),







            "status": (



                data.get(



                    "status"



                )



            ),







            "raw": data,



        }







    # ============================================================

    # OPPOGLOBE CARWASH PAYMENT ENTRYPOINT

    # ============================================================



    def initialize_payment(self, payment, request):
        """
        Entry point expected by carwash.views.create_payment().

        Creates a hosted Yoco checkout, stores the gateway reference on the
        CarWashPayment record, marks it as processing, and returns the checkout
        URL that map.html redirects the customer to.
        """

        if payment is None:
            raise ValueError("Payment is required.")

        if request is None:
            raise ValueError("Request is required.")

        if not self.is_configured():
            raise ValueError(
                "Yoco is not configured. Set YOCO_SECRET_KEY and restart Django."
            )

        wash_request = payment.wash_request

        success_url = request.build_absolute_uri(
            f"/carwash/payments/{payment.id}/success/"
        )
        cancel_url = request.build_absolute_uri(
            f"/carwash/payments/{payment.id}/cancel/"
        )
        failure_url = request.build_absolute_uri(
            f"/carwash/payments/{payment.id}/failed/"
        )

        result = self.create_checkout(
            amount=payment.gross_amount,
            currency=payment.currency or self.default_currency,
            reference=str(payment.id),
            success_url=success_url,
            cancel_url=cancel_url,
            failure_url=failure_url,
            metadata={
                "payment_id": str(payment.id),
                "wash_request_id": str(wash_request.id),
                "customer_id": str(wash_request.customer_id),
                "business_id": str(wash_request.business_id),
                "platform_commission": str(payment.platform_commission),
                "provider_amount": str(payment.provider_amount),
                "payment_method": payment.payment_method,
                "settlement_mode": payment.settlement_mode,
            },
        )

        if not result.get("success"):
            raise ValueError(
                result.get(
                    "error",
                    "Yoco checkout could not be created."
                )
            )

        checkout_id = result.get("checkout_id")
        redirect_url = result.get("redirect_url")

        if not checkout_id:
            raise ValueError(
                "Yoco created the checkout but did not return a checkout ID."
            )

        if not redirect_url:
            raise ValueError(
                "Yoco created the checkout but did not return a redirect URL."
            )

        payment.gateway_reference = str(checkout_id)
        payment.gateway_response = {
            "checkout_id": str(checkout_id),
            "redirect_url": redirect_url,
            "reference": result.get("reference"),
            "status": result.get("status"),
        }
        payment.status = "processing"

        payment.save(
            update_fields=[
                "gateway_reference",
                "gateway_response",
                "status",
                "updated_at",
            ]
        )

        return {
            "success": True,
            "gateway": self.code,
            "gateway_name": self.name,
            "checkout_id": checkout_id,
            "checkout_url": redirect_url,
            "redirect_url": redirect_url,
            "payment_url": redirect_url,
            "reference": result.get("reference"),
            "requires_redirect": True,
            "status": result.get("status") or "processing",
            "message": "Continue to Yoco to complete payment.",
        }


    # ============================================================



    # GENERIC PAYMENT METHOD



    # ============================================================







    def initiate_payment(



        self,



        *,



        amount,



        success_url,



        cancel_url,



        failure_url=None,



        reference=None,



        metadata=None,



        currency="ZAR",



        **kwargs,



    ):



        """



        Generic interface used by OppoGlobe's



        payment system.







        Internally this creates a Yoco checkout.



        """







        return self.create_checkout(







            amount=amount,







            success_url=(



                success_url



            ),







            cancel_url=(



                cancel_url



            ),







            failure_url=(



                failure_url



            ),







            reference=(



                reference



            ),







            metadata=(



                metadata



            ),







            currency=(



                currency



            ),







            idempotency_key=(



                kwargs.get(



                    "idempotency_key"



                )



            ),



        )







    # ============================================================



    # GET CHECKOUT



    # ============================================================







    def get_checkout(



        self,



        checkout_id,



    ):



        """



        Retrieve a Yoco checkout.







        Useful when verifying the status



        of an existing payment.



        """







        if not checkout_id:







            return {







                "success": False,







                "error": (



                    "Checkout ID "



                    "is required."



                ),



            }







        if not self.is_configured():







            return {







                "success": False,







                "error": (



                    "Yoco is not configured."



                ),



            }







        try:







            response = requests.get(







                (



                    f"{self.BASE_URL}"



                    f"/checkouts/"



                    f"{checkout_id}"



                ),







                headers=(



                    self._headers()



                ),







                timeout=30,



            )







        except (



            requests.RequestException



        ) as exc:







            logger.exception(



                "Yoco checkout lookup failed."



            )







            return {







                "success": False,







                "error": (



                    "Could not connect "



                    "to Yoco."



                ),







                "exception": (



                    str(exc)



                ),



            }







        try:







            data = (



                response.json()



            )







        except ValueError:







            data = {}







        if not response.ok:







            return {







                "success": False,







                "error": (







                    data.get(



                        "message"



                    )







                    or data.get(



                        "error"



                    )







                    or (



                        "Could not retrieve "



                        "Yoco checkout."



                    )



                ),







                "status_code": (



                    response.status_code



                ),







                "response": (



                    data



                ),



            }







        return {







            "success": True,







            "gateway": (



                self.code



            ),







            "checkout_id": (



                data.get(



                    "id"



                )



                or checkout_id



            ),







            "status": (



                data.get(



                    "status"



                )



            ),







            "amount": (



                data.get(



                    "amount"



                )



            ),







            "currency": (



                data.get(



                    "currency"



                )



            ),







            "raw": data,



        }







    # ============================================================



    # REFUND



    # ============================================================







    def refund(



        self,



        checkout_id,



        amount=None,



        metadata=None,



    ):



        """



        Refund a Yoco payment.







        amount=None:



            attempt full refund







        amount=Decimal("50.00"):



            refund R50.00



        """







        if not checkout_id:







            return {







                "success": False,







                "gateway": (



                    self.code



                ),







                "error": (



                    "Checkout ID "



                    "is required."



                ),



            }







        if not self.is_configured():







            return {







                "success": False,







                "gateway": (



                    self.code



                ),







                "error": (



                    "Yoco is not configured."



                ),



            }







        payload = {}







        if amount is not None:







            try:







                payload[



                    "amount"



                ] = (



                    self.amount_to_cents(



                        amount



                    )



                )







            except ValueError as exc:







                return {







                    "success": False,







                    "gateway": (



                        self.code



                    ),







                    "error": (



                        str(exc)



                    ),



                }







        if metadata:







            payload[



                "metadata"



            ] = (



                metadata



            )







        idempotency_key = (



            str(



                uuid.uuid4()



            )



        )







        try:







            response = (



                requests.post(



                    (



                        f"{self.BASE_URL}"



                        f"/checkouts/"



                        f"{checkout_id}"



                        "/refund"



                    ),







                    headers=(



                        self._headers(



                            idempotency_key



                        )



                    ),







                    json=payload,







                    timeout=30,



                )



            )







        except (



            requests.RequestException



        ) as exc:







            logger.exception(



                "Yoco refund failed."



            )







            return {







                "success": False,







                "gateway": (



                    self.code



                ),







                "error": (



                    "Could not connect "



                    "to Yoco."



                ),







                "exception": (



                    str(exc)



                ),



            }







        try:







            data = (



                response.json()



            )







        except ValueError:







            data = {}







        if not response.ok:







            logger.error(



                (



                    "Yoco refund "



                    "failed. HTTP %s: %s"



                ),



                response.status_code,



                data,



            )







            return {







                "success": False,







                "gateway": (



                    self.code



                ),







                "error": (







                    data.get(



                        "message"



                    )







                    or data.get(



                        "error"



                    )







                    or (



                        "Yoco refund failed."



                    )



                ),







                "status_code": (



                    response.status_code



                ),







                "response": (



                    data



                ),



            }







        return {







            "success": True,







            "gateway": (



                self.code



            ),







            "checkout_id": (



                checkout_id



            ),







            "refund_id": (







                data.get(



                    "refundId"



                )







                or data.get(



                    "id"



                )



            ),







            "status": (



                data.get(



                    "status"



                )



            ),







            "message": (



                data.get(



                    "message"



                )



                or "Refund processed."



            ),







            "raw": data,



        }







    # ============================================================



    # WEBHOOK HELPERS



    # ============================================================







    def parse_webhook(



        self,



        payload,



    ):



        """



        Normalise a Yoco webhook payload.







        IMPORTANT:



        This does NOT yet verify the webhook signature.







        Signature verification should happen before



        trusting the webhook and marking a payment paid.



        """







        if not isinstance(



            payload,



            dict,



        ):







            return {







                "success": False,







                "error": (



                    "Invalid webhook payload."



                ),



            }







        event_type = (







            payload.get(



                "type"



            )







            or payload.get(



                "event"



            )







            or payload.get(



                "eventType"



            )







            or ""



        )







        data = (



            payload.get(



                "data"



            )



            or {}



        )







        obj = (







            data.get(



                "object"



            )







            if isinstance(



                data,



                dict,



            )







            else {}



        )







        if not obj:







            obj = (



                data



                if isinstance(



                    data,



                    dict,



                )



                else {}



            )







        metadata = (



            obj.get(



                "metadata"



            )



            or payload.get(



                "metadata"



            )



            or {}



        )







        checkout_id = (







            obj.get(



                "checkoutId"



            )







            or obj.get(



                "checkout_id"



            )







            or obj.get(



                "id"



            )







            or payload.get(



                "checkoutId"



            )



        )







        status = (







            obj.get(



                "status"



            )







            or payload.get(



                "status"



            )



        )







        return {







            "success": True,







            "gateway": (



                self.code



            ),







            "event_type": (



                event_type



            ),







            "checkout_id": (



                checkout_id



            ),







            "status": (



                status



            ),







            "reference": (



                metadata.get(



                    "reference"



                )



            ),







            "payment_id": (



                metadata.get(



                    "payment_id"



                )



            ),







            "wash_request_id": (



                metadata.get(



                    "wash_request_id"



                )



            ),







            "metadata": (



                metadata



            ),







            "raw": (



                payload



            ),



        }