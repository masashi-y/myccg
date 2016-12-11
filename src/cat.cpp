
#include "cat.h"
#include "utils.h"


namespace myccg {
namespace cat {

const char* slashes = "/\\|";
Feat kNONE      = Feature::Parse("");
Feat kNB        = Feature::Parse("nb");


template<> Cat Compose<0>(Cat head, const Slash& op, Cat tail) {
    return Make(head, op, tail->GetRight());
}

template<> bool Category::HasFunctorAtLeft<0>() const {
    return this->IsFunctor();
}

template<> bool Category::HasFunctorAtRight<0>() const {
    return this->IsFunctor();
}

template<> Cat Category::GetLeft<0>() const { return this; }
template<> Cat Category::GetRight<0>() const { return this; }

std::string AtomicCategory::ToStrWithoutFeat() const {
#ifdef JAPANESE
    return type_;
#else
    std::string res(ToStr());
    utils::ReplaceAll(&res, "[X]", "");
    utils::ReplaceAll(&res, "[nb]", "");
    return res;
#endif
}

Cat Category::Parse(const std::string& cat) {
    Cat res;
    if (Cacheable::Count(cat) > 0) {
        return Cacheable::Get<Cat>(cat);
    } else {
        const std::string name = utils::DropBrackets(cat);
        if (Cacheable::Count(name) > 0) {
            res = Cacheable::Get<Cat>(name);
        } else {
            res = ParseUncached(name);
            if (name != cat) {
                res->RegisterCache(name);
            }
        }
        res->RegisterCache(cat);
        return res;
    }
}


Cat Category::ParseUncached(const std::string& cat) {
    std::string new_cat(cat);
    std::string semantics;
    if (new_cat.back() == '}') {
        int open_idx = new_cat.rfind("{");
        semantics = new_cat.substr(open_idx + 1, new_cat.size() - open_idx - 1);
        new_cat = new_cat.substr(0, open_idx);
    } else {
        semantics = "";
    }
    new_cat = utils::DropBrackets(new_cat);
    // utils::FindNonNestedChar enforces left associativity
    int op_idx = utils::FindNonNestedChar(new_cat, slashes);

    if (op_idx == -1) {
        int feat_idx = new_cat.find("[");
        if (feat_idx > -1) {
            std::string type = new_cat.substr(0, feat_idx);
            std::string feat_str = new_cat.substr(
                    feat_idx + 1, new_cat.find("]", feat_idx) - feat_idx - 1);
            Feat feat = Feature::Parse(feat_str);
            return new AtomicCategory(type, feat, semantics);
        }
        return new AtomicCategory(new_cat, kNONE, semantics);
    } else {
        Cat left = Category::Parse(new_cat.substr(0, op_idx));
        Slash slash = Slash(new_cat[op_idx]);
        Cat right = Category::Parse(new_cat.substr(op_idx + 1));
        return new Functor(left, slash, right, semantics);
    }
}

Cat Category::Substitute(Feat feat) const {
    if (feat->IsEmpty()) return this;
    return Category::Parse(std::move(feat->SubstituteWildcard(str_)));
}

Cat Make(Cat left, const Slash& op, Cat right) {
    return Category::Parse(left->WithBrackets() + op.ToStr() + right->WithBrackets());
}

Cat CorrectWildcardFeatures(Cat to_correct, Cat match1, Cat match2) {
    return to_correct->Substitute(match1->GetSubstitution(match2));
}



} // namespace cat
} // namespace myccg
