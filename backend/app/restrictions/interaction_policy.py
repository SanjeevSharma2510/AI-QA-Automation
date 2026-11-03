
class InteractionPolicy:

    def __init__(
        self,
        approved_dropdowns=None,
        approved_tabs=None
    ):

        self.approved_dropdowns = approved_dropdowns or []
        self.approved_tabs = approved_tabs or []

        self.blocked_actions = [
            "delete",
            "remove",
            "submit",
            "save",
            "payment",
            "checkout",
            "logout",
            "signout",
            "purchase"
        ]

    class InteractionPolicy:

        def __init__(
                self,
                approved_dropdowns=None,
                approved_tabs=None
        ):
            self.approved_dropdowns = approved_dropdowns or []
            self.approved_tabs = approved_tabs or []

            self.blocked_actions = [
                "delete",
                "remove",
                "submit",
                "save",
                "payment",
                "checkout",
                "logout",
                "signout",
                "purchase"
            ]

        def can_interact_with_dropdown(self, selector):
            return selector in self.approved_dropdowns

        def can_click_tab(self, selector):
            return selector in self.approved_tabs

        def is_safe_label(self, label):
            normalized_label = label.lower().strip()

            return not any(
                word in normalized_label
                for word in self.blocked_actions
            )
