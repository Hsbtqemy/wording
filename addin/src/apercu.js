/**
 * La vue d'ensemble, dans son dialogue.
 *
 * ⚠️ CE CODE ETAIT EN LIGNE DANS apercu.html, et c'est pour ca qu'il a casse
 * sans que rien ne le voie. Ni la parite ni la batterie du volet ne peuvent
 * atteindre un script ecrit dans un fichier HTML : il n'y a rien a importer.
 * Sorti ici, il passe sous le meme faux Office que le volet.
 *
 * Le dialogue partage l'origine du volet, donc son localStorage : il relit
 * l'etat tout seul. Le volet ne lui passe que la cle et la graine.
 */

import { svg_apercu } from "./composition.js";
import { Paysage } from "./paysage.js";

// Au-dela, on considere que le volet ne repondra plus. Trois secondes : le
// dialogue s'ouvre en quelques dizaines de millisecondes, et l'aller-retour
// est local.
export const ATTENTE_VOLET = 3000;

export function dessiner(cle, graine, doc = document) {
  const hote = doc.getElementById("paysage");
  const mot = doc.getElementById("mot");
  try {
    const paysage = Paysage.depuis(localStorage.getItem(cle));
    const plants = paysage.etat().plants;
    if (!plants.length) {
      mot.textContent =
        "Rien n'a encore pousse. C'est normal : il faut ecrire un peu.";
      return false;
    }
    mot.textContent = "";
    hote.innerHTML = svg_apercu(plants, hote.clientHeight || 520, graine);
    return true;
  } catch (e) {
    // ⚠️ Un dialogue blanc ne se diagnostique pas. Une panne qui se nomme, si.
    mot.textContent = `Le paysage n'a pas pu etre relu (${e.name}).`;
    console.warn("apercu : lecture impossible", e);
    return false;
  }
}

/**
 * La poignee de main avec le volet, en trois temps.
 *
 * ⚠️ « pret » NE PART QU'APRES LE RAPPEL DE addHandlerAsync, et c'est tout
 * l'objet de cette fonction. Le code d'avant enchainait :
 *
 *     Office.context.ui.addHandlerAsync(type, handler);   // asynchrone
 *     Office.context.ui.messageParent("pret");            // tout de suite
 *
 * addHandlerAsync est asynchrone. Dire « pret » sans attendre son rappel
 * laisse une fenetre pendant laquelle la reponse du volet arrive alors que
 * PERSONNE NE L'ECOUTE — et comme le volet ne repond qu'une fois, le dialogue
 * reste vide pour toujours. La course se perdait d'autant plus souvent que le
 * volet repondait vite, ce qu'il est devenu le jour ou l'ecriture a ete
 * amortie et le dessin identique cesse d'etre repose (decision 12).
 */
export function demarrer_apercu(bureau = Office, doc = document) {
  let minuteur = null;

  bureau.context.ui.addHandlerAsync(
    bureau.EventType.DialogParentMessageReceived,
    (arg) => {
      // Le volet a repondu : plus besoin du garde-temps, et le laisser courir
      // retiendrait le dialogue eveille pour rien.
      if (minuteur !== null) clearTimeout(minuteur);
      const { cle, graine } = JSON.parse(arg.message);
      dessiner(cle, graine, doc);
    },
    () => {
      // L'ecouteur est pose : on peut parler.
      bureau.context.ui.messageParent("pret");
      // Et si le volet ne repond pas, on le dit plutot que de rester blanc.
      minuteur = setTimeout(() => {
        minuteur = null;
        doc.getElementById("mot").textContent =
          "Le volet n'a pas repondu. Fermer cette fenetre et reessayer.";
      }, ATTENTE_VOLET);
    },
  );
}
