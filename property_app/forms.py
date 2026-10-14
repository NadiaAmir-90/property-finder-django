
from django import forms


class PropertySearchForm(forms.Form):
    city = forms.CharField(
        required=False,
        max_length=100,
        label="City",
        widget=forms.TextInput(
            attrs={"placeholder": "e.g. Destin"}
        ),
    )

    keyword = forms.CharField(
        required=False,
        max_length=100,
        label="Keyword",
        widget=forms.TextInput(
            attrs={"placeholder": "Beach house, apartment..."}
        ),
    )

    min_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Minimum price",
    )

    max_price = forms.DecimalField(
        required=False,
        min_value=0,
        label="Maximum price",
    )

    bedrooms = forms.IntegerField(
        required=False,
        min_value=0,
        label="Minimum bedrooms",
    )

    property_type = forms.CharField(
        required=False,
        max_length=50,
        label="Property type",
        widget=forms.TextInput(
            attrs={"placeholder": "House, apartment..."}
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get("min_price")
        max_price = cleaned_data.get("max_price")

        if (
            min_price is not None
            and max_price is not None
            and min_price > max_price
        ):
            self.add_error(
                "max_price",
                "Maximum price must be greater than or equal to minimum price.",
            )

        return cleaned_data
