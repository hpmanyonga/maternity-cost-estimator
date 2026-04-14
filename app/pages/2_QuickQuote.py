                        # Send automated emails
                        try:
                            from engine.email_sender import send_client_confirmation, send_team_notification
                            if email.strip():
                                send_client_confirmation(
                                    name=full_name.strip(), email=email.strip(),
                                    noh_low=estimate_low, noh_high=estimate_high,
                                    ffs_low=0, ffs_high=0,
                                    source="QuickQuote",
                                )
                            send_team_notification(
                                name=full_name.strip(), email=email.strip() or "",
                                phone=mobile.strip(), province="",
                                timing=gestation_group, birth_type=delivery_ui,
                                complexity=quote.complexity_tier,
                                noh_low=estimate_low, noh_high=estimate_high,
                                source="QuickQuote",
                            )
                             
                            # Create calendar callback event
                            try:
                                from engine.calendar_manager import create_callback_event
                                create_callback_event(
                                    full_name=full_name.strip(),
                                    email=email.strip() or "",
                                    mobile=mobile.strip(),
                                    province="",
                                    gestation_group=gestation_group,
                                    delivery_ui=delivery_ui,
                                    complexity_tier=quote.complexity_tier,
                                    estimate_low=int(estimate_low),
                                    estimate_high=int(estimate_high),
                                )
                            except Exception:
                                pass
                        except Exception:
                            pass
