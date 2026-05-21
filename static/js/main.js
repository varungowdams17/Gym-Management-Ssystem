document.addEventListener("DOMContentLoaded", function () {
  const deleteForms = document.querySelectorAll("form[action*='delete']");
  deleteForms.forEach((form) => {
    form.addEventListener("submit", function (event) {
      if (!confirm("Are you sure you want to delete this record?")) {
        event.preventDefault();
      }
    });
  });

  const popupOffer = document.getElementById("popupOffer");
  const popupOfferText = document.getElementById("popupOfferText");
  if (popupOffer && popupOfferText) {
    const messages = [
      "Save 15% on your first trainer session.",
      "Unlock 2 months free with annual membership.",
      "Free nutrition plan with premium signup.",
      "Bring a friend and both get 10% off.",
    ];
    let index = 0;

    function showPopup() {
      popupOfferText.textContent = messages[index];
      popupOffer.classList.add("visible");
      setTimeout(() => popupOffer.classList.remove("visible"), 5000);
      index = (index + 1) % messages.length;
    }

    showPopup();
    setInterval(showPopup, 9000);
  }
});
