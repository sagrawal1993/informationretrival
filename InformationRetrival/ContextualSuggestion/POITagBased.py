"""
This module contains the code for the tag based user profiling Recommender systems.
It requires user's seen POI's along its tag and the rating given to them on a given scale.
This method will simply rank the preferences for the given user.

1. Tag Embedding:: Representation vector for tags.
2. POI embedding:: based on centroid.
3. User Profile:: Positive profile, Negative profile, Neutral Profile.
4. Parameter finding:: For Rocchio, it required to be discrete optimization problem, where variable's value will for checking output.
5. Learning of the mapping can only be possible in the pos-neg-neu methods, as it will produce a feature vector.
"""

"""
This module will contains method to recomment
"""

from TextAnalysislib.InformationRetrival import AbstractIR
from analysislib import clustering, optimization
from sklearn.metrics.pairwise import cosine_similarity
from InformationRetrival.Measures import TREC
from analysislib import ranking

class AbstractDataSource:
    def getCandidateArticles(self, user_id):
        pass

    def getStoreUserProfile(self, user_id):
        """
        Get the user profile from storage.
        :param user_id:
        :type user_id:
        :return:
        :rtype:
        """
        pass

    def storeUserProfile(self, user_id, profile_json):
        """
        Will store the user's created profile in storage, means store all of its parameters as well.
        :param user_id:
        :type user_id:
        :param profile_json:
        :type profile_json:
        :return:
        :rtype:
        """
        pass

    def getUserPreferences(self, user_id):
        """
        Provide the documents user rated.
        :param user_id: user's unique id.
        :type user_id: int
        :return: the list of json contains documentId, rating and tags.
        :rtype: list of dict.
        """
        pass

    def getArticleTags(self, user_id, article_id):
        """
        Returns the tags corresponding to article_id.
        :param article_id:
        :type article_id:
        :return:
        :rtype:
        """
        pass

    def getOptimizationInfo(self, user_id):
        """
        This will get the info required for search optimization problems.
        :param user_id:
        :type user_id:
        :return:
        :rtype:
        """
        pass

    def storeOptimizationInfo(self, user_id, param_map):
        """
        This will store the optimization related info to storage.
        :param user_id:
        :type user_id:
        :param param_map:
        :type param_map:
        :return:
        :rtype:
        """
        pass

class WordEmbeddingBased(AbstractIR):

    """
    query:: {"id":1, "body":
    {"group": "Family", "season":"Summer", "trip_type":"Holiday", "duration":"Weekend trip",
    "location":{"id":152,"name":"Chicago","state":"IL","lat":41.85003,"lng":-87.65005},
    "person": {"gender": "Male", "age": 23, "id": "A00126103VB6TFM3EITH9",
    "preferences":[
    {"documentId":"TRECCS-00247633-160","rating":3,"tags":["Museums"]},
    {"documentId":"TRECCS-00018097-160","rating":3,"tags":["Farmer's markets"]},
    {"documentId":"TRECCS-00086564-160","rating":3},
    {"documentId":"TRECCS-00086340-160","rating":1,"tags":["Bar-hopping"]},
    {"documentId":"TRECCS-00086298-160","rating":-1},
    {"documentId":"TRECCS-00018094-160","rating":3,"tags":["Theatre"]},
    {"documentId":"TRECCS-00247656-160","rating":3,"tags":["Bar-hopping"]},
    {"documentId":"TRECCS-00018110-160","rating":2,"tags":["Shopping for food","Markets","Organic Food"]},
    {"documentId":"TRECCS-00675013-160","rating":3,"tags":["Fine Dining"]},
    {"documentId":"TRECCS-00087026-160","rating":3,"tags":["Fine Dining"]},
    {"documentId":"TRECCS-00086310-160","rating":3},
    {"documentId":"TRECCS-00087258-160","rating":4,"tags":["Museums","Art Galleries"]}
    ]}}}


    This code expect preferences to have tags.
    """
    def __init__(self, datasource, tag_embedding, profile_vector="unweighted", profile_type="individual", ranking="rocchio", rating_shift=2, opt_name=None, opt_param=None, qrel_level="multi"):
        super().__init__(datasource)
        self.tag_embedding = tag_embedding
        self.profile_vector = profile_vector
        self.rating_shift = rating_shift
        self.profile_type = profile_type
        self.ranking = ranking
        self.opt = optimization.getSearchOptimizer(opt_name, opt_param)
        self.qrel_level = qrel_level
        if profile_vector == "weighted":
            self.doc_combiner = clustering.getClusterEmbeddingFromPoints("weightedCentroid", {"dim": self.tag_embedding.size})
        else:
            self.doc_combiner = clustering.getClusterEmbeddingFromPoints("centroid", {"dim": self.tag_embedding.size})
        print("This is instance for getting articles recommendation based on word embedding")

    def __getProfile(self, preferences):
        pos_rating_list = []
        neu_rating_list = []
        neg_rating_list = []
        pos_doc_embedding_list = []
        neg_doc_embedding_list = []
        neu_doc_embedding_list = []

        for doc in preferences:
            if 'rating' in doc and 'tags' in doc and len(doc['tags']) > 0 and doc['rating'] != -1:
                rating = doc['rating']
                doc_embedding = self.tag_embedding.get_doc_embedding(doc['tags'])
                #print(doc_embedding, rating, doc)
                if rating > 2:
                    pos_rating_list.append(rating - 1)
                    pos_doc_embedding_list.append(doc_embedding)
                elif rating == 2:
                    neu_rating_list.append(1)
                    neu_doc_embedding_list.append(doc_embedding)
                else:
                    neg_rating_list.append(rating - 3)
                    neg_doc_embedding_list.append(doc_embedding)

        parm_map = {}
        if self.profile_type == "combined":
            parm_map["weights"] = pos_rating_list + neu_rating_list + neg_rating_list
            doc_embedding_list = pos_doc_embedding_list + neu_doc_embedding_list + neg_doc_embedding_list
            profile_vec = self.doc_combiner.getClusterRepresentation(doc_embedding_list, parm_map)
            return profile_vec

        parm_map["weights"] = pos_rating_list
        pos_profile_vec = self.doc_combiner.getClusterRepresentation(pos_doc_embedding_list, parm_map)
        parm_map["weights"] = neu_rating_list
        neu_profile_vec = self.doc_combiner.getClusterRepresentation(neu_doc_embedding_list, parm_map)
        parm_map["weights"] = neg_rating_list
        neg_profile_vec = self.doc_combiner.getClusterRepresentation(neg_doc_embedding_list, parm_map)
        #print(pos_profile_vec, neu_profile_vec, neg_profile_vec)
        return pos_profile_vec, neu_profile_vec, neg_profile_vec

    def fit(self, user_ids, fit_type="search", score_file=None, param_type="all", store_profile=False, measure="ndcg_cut_5"):
        if fit_type == "search":
            self.__search_fit(user_ids, score_file, param_type, store_profile, measure)
        else:
            self.__learning_to_rank(user_ids, param_type)
        return

    def __learning_to_rank(self, user_ids, param_type):
        user_profile = {}
        final_param_map = {}
        all_vec = []
        all_rating = []
        for user_id in user_ids:
            preferences = self.datasource.getUserPreferences(user_id)
            profile_vector = self.__getProfile(preferences)
            user_profile[user_id] = (profile_vector, preferences)
            vec_list, rating_list = self.__get_vector_rating_list(profile_vector, preferences)
            final_param_map[str(user_id)] = {}
            final_param_map[str(user_id)]['user_prof'] = profile_vector
            final_param_map[str(user_id)]['preference'] = preferences
            if param_type == "all":
                all_vec += vec_list
                all_rating += rating_list
            else:
                learner = ranking.getRanker(self.ranking)
                learner.fit(vec_list, rating_list)
                final_param_map[str(user_id)]["learner"] = learner
        if param_type == "all":
            learner = ranking.getRanker(self.ranking)
            learner.fit(all_vec, all_rating)
            for user_id in user_ids:
                final_param_map[str(user_id)]["learner"] = learner
        self.full_info_map = final_param_map
        return

    def __get_vector_rating_list(self, user_profile, preferences):
        vec_list = self.__get_learning_vec(user_profile, preferences)
        rating = []
        for doc in preferences:
            if 'rating' in doc:
                rating.append(doc['rating'])
            else:
                rating.append(0)
        return vec_list, rating

    def __search_fit(self, user_ids, score_file=None, param_type="all", store_profile=False, measure="ndcg_cut_5", store_opt=True):
        """
        This function will create the user profiles for the user's id given, and will store according to the given function.
        :param user_ids:
        :type user_ids:
        :param param_type:
        :type param_type:
        :param store_profile:
        :type store_profile:
        :return:
        :rtype:
        """
        print("start search fitting")
        final_param_map = {}
        for user_id in user_ids:
            preferences = self.datasource.getUserPreferences(user_id)
            profile_vector = self.__getProfile(preferences)
            if score_file is None:
                arg_map = {}
                arg_map['profile'] = profile_vector
                arg_map['candidate'] = preferences
                arg_map['user_id'] = user_id
                full_map = self.opt.traverse_search_space(self.score_file_generator, arg_map)
                if store_opt:
                    self.datasource.storeOptimizationInfo(user_id, full_map)
            elif user_id != 'all':
                full_map = self.datasource.getOptimizationInfo(str(user_id))

            final_param_map[str(user_id)] = {}
            final_param_map[str(user_id)]['user_prof'] = profile_vector
            final_param_map[str(user_id)]['preference'] = preferences
            if param_type != 'all':
                args = {}
                args['measure'] = measure
                args['user_id'] = str(user_id)
                args['profile'] = profile_vector
                args['candidate'] = preferences
                args['score_map'] = full_map
                final_param_map[str(user_id)]["final_param"] = self.opt.maximize(self.score_selector, args)
            print("done with " + str(user_id))

        if param_type == 'all':
            full_map = self.datasource.getOptimizationInfo('all')
            args = {}
            args['qid'] = 'all'
            args['measure'] = measure
            args['score_map'] = full_map
            params = self.opt.maximize(self.score_selector, args)
            for user_id in user_ids:
                final_param_map[str(user_id)]['final_param'] = params

        if store_profile:
            for user_id in user_ids:
                self.datasource.storeUserProfile(user_id, final_param_map[str(user_id)])
        self.full_info_map = final_param_map
        return

    def score_selector(self, param, args):
        score_map = args["score_map"]
        measure = args["measure"]
        qid = args["qid"]
        if score_map is None:
            score_map = self.score_file_generator(param, args)
        measure_score = score_map[str(param[0])][str(param[1])][qid]
        return measure_score[measure]

    def score_file_generator(self, param, arg):
        ranked_poi = []
        pref_list = []
        user_prof = arg['profile']
        candidate = arg['candidate']
        user_id = arg['user_id']
        if self.ranking == "rocchio":
            cand_score = self.rocchioRanker(user_prof, [param[0], 1, param[1]], candidate)
        else:
            cand_score = self.similarityRanker(user_prof, [param[0], 1, param[1]], candidate)
        ranked_poi.append(cand_score)
        pref_list.append(candidate)
        #print(ranked_poi)
        TREC.create_qrel_from_preferences(pref_list, [user_id], "qrel.txt", level=self.qrel_level)
        TREC.create_output_file(ranked_poi, [user_id], "temp.txt")
        param_score = TREC.get_score("qrel.txt", "temp.txt")
        return param_score

    def rocchioRanker(self, user_profile, params, candidate_suggestion):
        print("started rocchio ranker")
        profile_vec = params[0] * user_profile[0] + params[1] * user_profile[1] + params[2] * user_profile[2]
        doc_id_score_map = {}
        for doc in candidate_suggestion:
            doc_vec = self.tag_embedding.get_doc_embedding(doc['tags'])
            doc_id_score_map[doc['documentId']] = cosine_similarity([profile_vec], [doc_vec])[0][0]
        return doc_id_score_map

    def similarityRanker(self, user_profile, params, candidate_suggestion):
        print("start similarity based ranker")
        doc_id_score_map = {}
        for doc in candidate_suggestion:
            doc_vec = self.tag_embedding.get_vec_tags(doc['tags'])
            temp = cosine_similarity([doc_vec], user_profile)
            doc_id_score_map[doc['documentId']] = cosine_similarity(temp, [params])[0][0]
        return doc_id_score_map

    def __get_learning_vec(self, user_profile, candidate_suggestion):
        vector_list = []
        for doc in candidate_suggestion:
            doc_vec = self.tag_embedding.get_vec_tags(doc['tags'])
            temp = cosine_similarity([doc_vec], user_profile)[0]
            vector_list.append(temp)
        return vector_list

    def learnedRank(self, user_profile, learner, candidate_suggestion):
        doc_id_score_map = {}
        vector_list = []
        for doc in candidate_suggestion:
            doc_vec = self.tag_embedding.get_vec_tags(doc['tags'])
            temp = cosine_similarity([doc_vec], user_profile)[0]
            vector_list.append(temp)
        score_list = learner.transform(vector_list)
        for i, doc in enumerate(candidate_suggestion):
            doc_id_score_map[doc['documentId']] = score_list[i]
        return doc_id_score_map

    def getArticles(self, user_id, params=None):
        candiate_articles = self.datasource.getCandidateArticles(user_id)
        detailed_candidate_article = []
        for article_id in candiate_articles:
            entry_map = {}
            entry_map['documentId'] = article_id
            entry_map['tags'] = self.datasource.getArticleTags(user_id, article_id)
            detailed_candidate_article.append(entry_map)
        if params is not None:
            a, b, value = params[0], params[1], -1
            user_prof = self.__getProfile(self.datasource.getUserPreferences(user_id))
        else:
            full_info = self.full_info_map[user_id]
            a, b, value = full_info['final_param']
            user_prof = full_info['user_prof']

        if self.ranking == "rocchio":
            cand_score = self.rocchioRanker(user_prof, [a, 1, b], detailed_candidate_article)
        elif self.ranking == "similarity":
            cand_score = self.similarityRanker(user_prof, [a, 1, b], detailed_candidate_article)
        elif params is None:
            learner = full_info['learner']
            cand_score = self.learnedRank(user_prof, learner, detailed_candidate_article)
        return cand_score